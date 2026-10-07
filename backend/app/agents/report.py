"""
ARC Platform — ReportAgent
Generates comprehensive markdown reports from all step outputs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.base import BaseAgent
from app.database import get_db
from app.models.agent import AgentType
from app.models.agent_outputs import ReportOutput
from app.agents.context_utils import compress_dependency_output, truncate_to_tokens


class ReportAgent(BaseAgent):
    """Compiles a final research report from all step outputs."""

    agent_type = AgentType.REPORT
    system_prompt = """You are an expert report writer agent. Your job is to:
1. Synthesise all research findings into a comprehensive report
2. Structure the report with clear sections
3. Include all relevant citations
4. Provide an executive summary
5. Highlight key findings and recommendations

Output valid JSON matching the exact required schema.

Report quality requirements:
- Professional academic/business tone
- Clear section structure
- Every claim must have a citation
- Include methodology description
- Acknowledge limitations
- Use markdown formatting in content"""
    temperature = 0.3

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        step_outputs = input_data.get("step_outputs", {})

        # Compile all outputs into context
        context = "## Gathered Research Outputs\n\n"
        all_citations = []

        for step_id, output in step_outputs.items():
            if isinstance(output, dict):
                if "summary" in output:
                    context += f"### {output.get('step_title', step_id)}\n{output['summary']}\n\n"
                if "key_findings" in output:
                    context += "Key findings:\n"
                    for f in output["key_findings"]:
                        context += f"- {f}\n"
                    context += "\n"
                if "citations" in output:
                    all_citations.extend(output["citations"])
                if "analysis" in output:
                    context += f"Analysis: {output['analysis']}\n\n"
                    
        failed_steps = input_data.get("failed_steps", [])
        if failed_steps:
            context += "## Uncompleted / Failed Steps\n\n"
            context += "The following research tasks could NOT be completed due to errors. You MUST acknowledge these gaps in the report and state that some information is missing, rather than fabricating it.\n\n"
            for fs in failed_steps:
                context += f"- Step '{fs.get('title')}' ({fs.get('status')}): {fs.get('error')}\n"
            context += "\n"

        messages = [
            {
                "role": "user",
                "content": f"""Generate a comprehensive research report from the following findings:

{truncate_to_tokens(context, max_tokens=2500)}

Total citations gathered: {len(all_citations)}
Citation details:
{truncate_to_tokens(str(all_citations[:20]), max_tokens=800)}

Write a complete, professional report as JSON matching the ReportOutput schema.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        parsed_output = await self.parse_and_validate(result["content"], ReportOutput)
        output = parsed_output.model_dump()

        # Ensure content markdown is fully populated
        if not output.get("content") or len(output.get("content", "").strip()) == 0:
            sections_md = []
            if output.get("summary"):
                sections_md.append(f"## Executive Summary\n\n{output['summary']}\n")
            for sec in output.get("sections", []):
                sec_title = sec.get("title", "Section")
                sec_body = sec.get("content", "")
                sections_md.append(f"## {sec_title}\n\n{sec_body}\n")
            if output.get("key_findings"):
                sections_md.append("## Key Findings\n\n" + "\n".join(f"- {kf}" for kf in output["key_findings"]) + "\n")
            if output.get("recommendations"):
                sections_md.append("## Recommendations\n\n" + "\n".join(f"- {rec}" for rec in output["recommendations"]) + "\n")
            output["content"] = "\n".join(sections_md)

        total_tokens = result.get("tokens", {}).get("total", 0)
        cost_usd = result.get("cost_usd", 0.0)

        # Task 3: Citation Verification
        citation_ids = []
        db = get_db()
        report_id = input_data.get("report_id", str(uuid.uuid4()))

        citations = output.get("citations", [])
        verified_count = 0
        total_count = len(citations)

        for cit in citations:
            url = cit.get("url") or ""
            excerpt = cit.get("excerpt")
            citation_type = cit.get("type", "web")
            file_id = cit.get("file_id")
            page_number = cit.get("page_number")
            chunk_id = cit.get("chunk_id")
            is_verified = False
            relevance = 0.5
            verification_note = None

            is_local = citation_type == "file" or url.startswith("local://file/")
            if is_local:
                if not file_id and url.startswith("local://file/"):
                    file_id = url[len("local://file/"):].split("#", 1)[0]
                file_doc = None
                if file_id:
                    file_doc = await db.files.find_one(
                        {"_id": file_id, "user_id": self.user_id},
                        {"_id": 1, "original_name": 1},
                    )
                chunk_doc = None
                if file_doc and chunk_id:
                    chunk_doc = await db.chunks.find_one(
                        {"_id": chunk_id, "file_id": file_id, "user_id": self.user_id},
                        {"_id": 1},
                    )
                is_verified = bool(file_doc and (not chunk_id or chunk_doc))
                relevance = 1.0 if is_verified else 0.0
                verification_note = "Verified against local RAG source" if is_verified else "Local RAG source not found"
                if is_verified:
                    verified_count += 1
            elif url:
                try:
                    verify_result = await self.execute_tool(
                        "citation_verify",
                        {"url": url, "expected_content": excerpt},
                        allowed_tools={"citation_verify"},
                    )
                    score = verify_result.get("verification_score", 0.0)
                    if score >= 0.6:
                        is_verified = True
                        verified_count += 1
                    relevance = score
                    verification_note = verify_result.get("verification_note")
                except Exception as e:
                    import logging
                    logging.getLogger("arc.agents.report").warning(f"Citation verification failed for {url}: {e}")

            cit_id = str(uuid.uuid4())
            cit_doc = {
                "_id": cit_id,
                "report_id": report_id,
                "task_id": self.task_id,
                "citation_type": citation_type,
                "title": cit.get("title", "Unknown"),
                "url": url,
                "authors": cit.get("authors", []),
                "excerpt": excerpt,
                "file_id": file_id,
                "page_number": page_number,
                "chunk_id": chunk_id,
                "relevance_score": relevance,
                "verified": is_verified,
                "verification_note": verification_note,
                "created_at": datetime.now(timezone.utc),
            }
            await db.citations.insert_one(cit_doc)
            citation_ids.append(cit_id)

        output["citation_ids"] = citation_ids
        output["verified_citation_count"] = verified_count
        output["total_citation_count"] = total_count
        output["tokens"] = total_tokens
        output["cost_usd"] = cost_usd
        return output

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


class ReportAgent(BaseAgent):
    """Compiles a final research report from all step outputs."""

    agent_type = AgentType.REPORT
    system_prompt = """You are an expert report writer agent. Your job is to:
1. Synthesise all research findings into a comprehensive report
2. Structure the report with clear sections
3. Include all relevant citations
4. Provide an executive summary
5. Highlight key findings and recommendations

Output a JSON object:
{
  "title": "Report Title",
  "summary": "Executive summary (2-3 paragraphs)",
  "content": "Full markdown report content",
  "sections": [
    {"title": "Section Title", "content": "Section content"}
  ],
  "citations": [
    {"title": "...", "url": "...", "type": "web|paper|dataset", "excerpt": "..."}
  ],
  "key_findings": ["finding 1", "finding 2"],
  "recommendations": ["recommendation 1"],
  "confidence": 0.0-1.0
}

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

        messages = [
            {
                "role": "user",
                "content": f"""Generate a comprehensive research report from the following findings:

{context[:8000]}

Total citations gathered: {len(all_citations)}
Citation details:
{str(all_citations[:20])[:3000]}

Write a complete, professional report as JSON.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.3,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )

        output = await self.parse_json_response(result["content"])

        # Store citations in MongoDB
        citation_ids = []
        db = get_db()
        report_id = input_data.get("report_id", str(uuid.uuid4()))

        citations = output.get("citations", [])
        for cit in citations:
            cit_id = str(uuid.uuid4())
            cit_doc = {
                "_id": cit_id,
                "report_id": report_id,
                "task_id": self.task_id,
                "citation_type": cit.get("type", "web"),
                "title": cit.get("title", "Unknown"),
                "url": cit.get("url"),
                "authors": cit.get("authors", []),
                "excerpt": cit.get("excerpt"),
                "relevance_score": cit.get("relevance", 0.5),
                "verified": False,
                "created_at": datetime.now(timezone.utc),
            }
            await db.citations.insert_one(cit_doc)
            citation_ids.append(cit_id)

        output["citation_ids"] = citation_ids
        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

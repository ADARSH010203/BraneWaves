"""
ARC Platform — ResearchAgent
Conducts web and paper research, summarises findings with citations.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.database import get_redis
from app.config import get_settings
from app.models.agent_outputs import ResearchOutput
from app.agents.context_utils import compress_dependency_output
import hashlib
import json
import logging

logger = logging.getLogger("arc.agents.research")


class ResearchAgent(BaseAgent):
    """Searches the web and academic papers, synthesises findings."""

    agent_type = AgentType.RESEARCH
    system_prompt = """You are an expert research agent. Your job is to:
1. Understand the research question or topic given to you
2. Use available tools to gather information
3. Synthesise the findings into a structured summary
4. Provide citations for every claim

Output valid JSON matching the exact required schema.
Be thorough, accurate, and always cite your sources."""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description") or input_data.get("description") or input_data.get("task_description") or input_data.get("query") or ""
        dep_outputs = input_data.get("dependency_outputs", {})

        # Build context from dependencies
        context = ""
        if dep_outputs:
            context = "\n\nPrevious findings:\n"
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict):
                    compressed = await compress_dependency_output(output)
                    context += f"- {compressed}\n"

        messages = [
            {
                "role": "user",
                "content": f"""Research the following topic and synthesise your findings:

**Topic:** {description}
{context}

Use the available tools (web_search, paper_search, vector_search) to find real facts, extract key findings, and cite sources.
Provide a comprehensive research summary as JSON matching the ResearchOutput schema.""",
            }
        ]

        settings = get_settings()
        cache_key = None
        redis_client = get_redis()

        if settings.ENABLE_AGENT_CACHE:
            prompt_text = messages[0]["content"] if messages else description
            hash_input = f"{prompt_text}_{settings.GROQ_MODEL}"
            cache_key = f"cache:agent:research:{hashlib.sha256(hash_input.encode()).hexdigest()}"
            
            try:
                cached_run = await redis_client.get(cache_key)
                if cached_run:
                    logger.info("Cache hit for research agent: cache_key=%s task_id=%s", cache_key, self.task_id)
                    cached_data = json.loads(cached_run)
                    parsed_output = await self.parse_and_validate(cached_data["content"], ResearchOutput)
                    output = parsed_output.model_dump()
                    output["tokens"] = cached_data.get("tokens", 0)
                    output["cost_usd"] = cached_data.get("cost_usd", 0.0)
                    output["cache_hit"] = True
                    return output
            except Exception as e:
                logger.warning("Cache check failed: %s", e)

        available_tools = ["web_search", "paper_search", "vector_search"]
        result = await self.run_agentic_loop(
            messages=messages,
            available_tools=available_tools,
            max_iterations=6
        )

        if settings.ENABLE_AGENT_CACHE and cache_key:
            try:
                await redis_client.set(cache_key, json.dumps(result), ex=settings.CACHE_TTL_SECONDS)
            except Exception as e:
                logger.warning("Cache set failed: %s", e)

        parsed_output = await self.parse_and_validate(result["content"], ResearchOutput)
        output = parsed_output.model_dump()
        
        # Bug 3: Verify citations at the research step to catch hallucinations early
        citations = output.get("citations", [])
        verified_citations = []
        for cit in citations:
            url = cit.get("url")
            excerpt = cit.get("excerpt")
            if url:
                try:
                    verify_result = await self.execute_tool("citation_verify", {
                        "url": url,
                        "expected_content": excerpt
                    })
                    score = verify_result.get("verification_score", 0.0)
                    if score >= 0.6:
                        cit["verified"] = True
                    else:
                        cit["verified"] = False
                except Exception:
                    cit["verified"] = False
            verified_citations.append(cit)
        
        output["citations"] = verified_citations

        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        output["cache_hit"] = False
        return output

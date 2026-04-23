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
import hashlib
import json
import logging

logger = logging.getLogger("arc.agents.research")


class ResearchAgent(BaseAgent):
    """Searches the web and academic papers, synthesises findings."""

    agent_type = AgentType.RESEARCH
    system_prompt = """You are an expert research agent. Your job is to:
1. Understand the research question or topic given to you
2. Use available tools (web_search, paper_search, vector_search) to gather information
3. Synthesise the findings into a structured summary
4. Provide citations for every claim

Output a JSON object:
{
  "summary": "Comprehensive summary of findings",
  "key_findings": ["finding 1", "finding 2", ...],
  "citations": [
    {"title": "...", "url": "...", "type": "web|paper", "excerpt": "relevant passage"}
  ],
  "confidence": 0.0-1.0,
  "gaps": ["areas where more research is needed"]
}

Be thorough, accurate, and always cite your sources."""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description", input_data.get("description", ""))
        dep_outputs = input_data.get("dependency_outputs", {})

        # Build context from dependencies
        context = ""
        if dep_outputs:
            context = "\n\nPrevious findings:\n"
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict) and "summary" in output:
                    context += f"- {output['summary'][:500]}\n"

        # Use tools to gather information
        search_results = {}
        try:
            search_results = await self.execute_tool("web_search", {"query": description[:200]})
        except Exception:
            pass

        paper_results = {}
        try:
            paper_results = await self.execute_tool("paper_search", {"query": description[:200]})
        except Exception:
            pass

        # RAG vector search
        rag_results = {}
        try:
            rag_results = await self.execute_tool("vector_search", {
                "query": description[:200],
                "user_id": self.user_id,
                "top_k": 5,
            })
        except Exception:
            pass

        # Synthesise with LLM
        tools_context = ""
        if search_results.get("results"):
            tools_context += f"\n\nWeb Search Results:\n{search_results['results'][:3000]}"
        if paper_results.get("results"):
            tools_context += f"\n\nAcademic Paper Results:\n{paper_results['results'][:3000]}"
        if rag_results.get("results"):
            tools_context += f"\n\nKnowledge Base Results:\n{rag_results['results'][:2000]}"

        messages = [
            {
                "role": "user",
                "content": f"""Research the following topic and synthesise your findings:

**Topic:** {description}
{context}
{tools_context}

Provide a comprehensive research summary as JSON.""",
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
                    output = await self.parse_json_response(cached_data["content"])
                    output["tokens"] = cached_data.get("tokens", 0)
                    output["cost_usd"] = cached_data.get("cost_usd", 0.0)
                    output["cache_hit"] = True
                    return output
            except Exception as e:
                logger.warning("Cache check failed: %s", e)

        result = await self.call_llm(
            messages,
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        if settings.ENABLE_AGENT_CACHE and cache_key:
            try:
                await redis_client.set(cache_key, json.dumps(result), ex=settings.CACHE_TTL_SECONDS)
            except Exception as e:
                logger.warning("Cache set failed: %s", e)

        output = await self.parse_json_response(result["content"])
        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        output["cache_hit"] = False
        return output

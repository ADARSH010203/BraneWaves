"""
ARC Platform — DataAgent
Searches for datasets, analyses data, provides statistical insights.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType


class DataAgent(BaseAgent):
    """Finds and analyses datasets relevant to the research task."""

    agent_type = AgentType.DATA
    system_prompt = """You are an expert data analysis agent. Your job is to:
1. Search for relevant datasets using the dataset_search tool
2. Analyse data using the python_sandbox tool if needed
3. Extract statistical insights and patterns
4. Present findings in a structured format

Output a JSON object:
{
  "datasets_found": [
    {"name": "...", "source": "...", "description": "...", "relevance": 0.0-1.0}
  ],
  "analysis": "Summary of data analysis",
  "statistics": {"key_metric": "value"},
  "visualizations": ["description of charts/plots generated"],
  "confidence": 0.0-1.0
}

Focus on data quality, relevance, and statistical rigour."""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description", input_data.get("description", ""))
        dep_outputs = input_data.get("dependency_outputs", {})

        # Search for datasets
        dataset_results = {}
        try:
            dataset_results = await self.execute_tool("dataset_search", {"query": description[:200]})
        except Exception:
            pass

        # Build context
        context = ""
        if dep_outputs:
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict):
                    context += f"\nPrevious step output: {str(output)[:500]}"

        dataset_context = ""
        if dataset_results.get("results"):
            dataset_context = f"\n\nDataset Search Results:\n{dataset_results['results'][:3000]}"

        messages = [
            {
                "role": "user",
                "content": f"""Analyse data related to the following topic:

**Topic:** {description}
{context}
{dataset_context}

If code analysis is needed, describe the analysis approach.
Provide your findings as JSON.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        output = await self.parse_json_response(result["content"])
        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

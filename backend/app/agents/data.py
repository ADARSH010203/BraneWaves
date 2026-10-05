"""
ARC Platform — DataAgent
Searches for datasets, analyses data, provides statistical insights.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.agent_outputs import DataOutput
from app.agents.context_utils import compress_dependency_output


class DataAgent(BaseAgent):
    """Finds and analyses datasets relevant to the research task."""

    agent_type = AgentType.DATA
    system_prompt = """You are an expert data analysis agent. Your job is to:
1. Search for relevant datasets using the dataset_search tool
2. Analyse data using the python_sandbox tool if needed
3. Extract statistical insights and patterns
4. Present findings in a structured format

Output valid JSON matching the exact required schema.
Focus on data quality, relevance, and statistical rigour."""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description") or input_data.get("description") or input_data.get("task_description") or input_data.get("query") or ""
        dep_outputs = input_data.get("dependency_outputs", {})

        # Build context
        context = ""
        if dep_outputs:
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict):
                    compressed = await compress_dependency_output(output)
                    context += f"\nPrevious step output: {compressed}"

        messages = [
            {
                "role": "user",
                "content": f"""Analyse data related to the following topic:

**Topic:** {description}
{context}

Use available tools (dataset_search, web_search, python_sandbox) to find real numeric data points, trends, and statistics.
Provide your complete findings as JSON matching the DataOutput schema.""",
            }
        ]

        available_tools = ["dataset_search", "web_search", "python_sandbox"]
        result = await self.run_agentic_loop(
            messages=messages,
            available_tools=available_tools,
            max_iterations=6
        )

        parsed_output = await self.parse_and_validate(result["content"], DataOutput)
        output = parsed_output.model_dump()
        
        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

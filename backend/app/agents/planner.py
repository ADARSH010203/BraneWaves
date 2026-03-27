"""
ARC Platform — PlannerAgent
Decomposes a complex research task into a dependency DAG of executable steps.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType


class PlannerAgent(BaseAgent):
    """
    Analyses the user's task and generates a structured execution plan
    as a list of steps with dependencies, types, and descriptions.
    """

    agent_type = AgentType.PLANNER
    system_prompt = """You are an expert research planning agent. Your job is to decompose a complex research task into a set of concrete, executable steps.

For each step, specify:
- title: A short descriptive title
- type: One of "research", "data", "code", "critique", "report"
- description: What should be done in this step
- depends_on: A list of step indices (0-indexed) that must complete before this step
- input_data: Any specific parameters or queries for this step

Output a valid JSON object with the following structure:
{
  "steps": [
    {
      "title": "...",
      "type": "research|data|code|critique|report",
      "description": "...",
      "depends_on": [],
      "input_data": {}
    }
  ],
  "confidence": 0.0-1.0,
  "rationale": "Brief explanation of the plan"
}

Rules:
- Keep steps focused and atomic
- Ensure proper dependency ordering (no cycles)
- Include a critique step to validate research findings
- Always end with a report step that depends on all prior steps
- Usually 3-10 steps for typical research tasks
- Mark independent steps as having no dependencies so they can run in parallel
"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        title = input_data.get("title", "")
        description = input_data.get("description", "")

        messages = [
            {
                "role": "user",
                "content": f"""Plan the following research task:

**Title:** {title}

**Description:** {description}

Generate a detailed execution plan as JSON.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.4,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        plan = await self.parse_json_response(result["content"])

        # Convert dependency indices to step IDs (will be assigned later)
        steps = plan.get("steps", [])
        for i, step in enumerate(steps):
            deps = step.get("depends_on", [])
            # Convert integer indices to string indices for now
            step["depends_on"] = [str(d) for d in deps if isinstance(d, int) and d < i]

        return {
            "steps": steps,
            "confidence": plan.get("confidence", 0.8),
            "rationale": plan.get("rationale", ""),
            "tokens": result["tokens"],
            "cost_usd": result["cost_usd"],
        }

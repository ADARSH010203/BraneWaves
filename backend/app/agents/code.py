"""
ARC Platform — CodeAgent
Generates and executes Python code in a sandboxed environment.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.agent_outputs import CodeOutput
from app.agents.context_utils import compress_dependency_output


class CodeAgent(BaseAgent):
    """Generates Python code and executes it in a sandboxed environment."""

    agent_type = AgentType.CODE
    system_prompt = """You are an expert Python coding agent. Your job is to:
1. Write Python code to solve the given problem
2. Ensure code is safe and doesn't access the filesystem or network unsafely
3. Execute code in a sandboxed environment using the python_sandbox tool
4. Interpret results and provide structured output

Output valid JSON matching the exact required schema.

Rules:
- Only use standard library and common data science packages (pandas, numpy, etc.)
- No file system access outside sandbox
- No network requests
- Code must be deterministic when possible
- Include error handling"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description") or input_data.get("description") or input_data.get("task_description") or input_data.get("query") or ""
        dep_outputs = input_data.get("dependency_outputs", {})

        context = ""
        if dep_outputs:
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict):
                    compressed = await compress_dependency_output(output)
                    context += f"\nPrevious step data: {compressed}"

        # Ask LLM to generate code
        messages = [
            {
                "role": "user",
                "content": f"""Write Python code to solve this task:

**Task:** {description}
{context}

Generate the code, execute it using the python_sandbox tool, and explain what it does. Output as JSON matching the CodeOutput schema.""",
            }
        ]

        available_tools = ["python_sandbox"]
        result = await self.run_agentic_loop(
            messages=messages,
            available_tools=available_tools,
            max_iterations=6
        )

        parsed_output = await self.parse_and_validate(result["content"], CodeOutput)
        output = parsed_output.model_dump()

        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

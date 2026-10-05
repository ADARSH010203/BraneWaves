"""
ARC Platform — CodeAgent
Generates and executes Python code in a sandboxed environment.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType


class CodeAgent(BaseAgent):
    """Generates Python code and executes it in a sandboxed environment."""

    agent_type = AgentType.CODE
    system_prompt = """You are an expert Python coding agent. Your job is to:
1. Write Python code to solve the given problem
2. Ensure code is safe and doesn't access the filesystem or network unsafely
3. Execute code in a sandboxed environment using the python_sandbox tool
4. Interpret results and provide structured output

Output a JSON object:
{
  "code": "the Python code you wrote",
  "explanation": "what the code does and why",
  "execution_result": "output from running the code",
  "success": true|false,
  "confidence": 0.0-1.0
}

Rules:
- Only use standard library and common data science packages (pandas, numpy, etc.)
- No file system access outside sandbox
- No network requests
- Code must be deterministic when possible
- Include error handling"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        description = input_data.get("step_description", input_data.get("description", ""))
        dep_outputs = input_data.get("dependency_outputs", {})

        context = ""
        if dep_outputs:
            for dep_id, output in dep_outputs.items():
                if isinstance(output, dict):
                    context += f"\nPrevious step data: {str(output)[:1000]}"

        # Ask LLM to generate code
        messages = [
            {
                "role": "user",
                "content": f"""Write Python code to solve this task:

**Task:** {description}
{context}

Generate the code and explain what it does. Output as JSON.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        output = await self.parse_json_response(result["content"])

        # Execute code in sandbox if provided — with retry loop
        code = output.get("code", "")
        if code:
            current_messages = list(messages)
            for attempt in range(3):
                try:
                    sandbox_result = await self.execute_tool("python_sandbox", {"code": code})
                    execution_output = sandbox_result.get("output", "")
                    success = sandbox_result.get("success", False)
                    output["execution_result"] = execution_output
                    output["success"] = success
                    if success:
                        break
                    # Code ran but failed — ask LLM to fix
                    if attempt < 2:
                        import logging
                        logging.getLogger("arc.agents.code").info(
                            "Code attempt %d failed for step %s, retrying with LLM fix",
                            attempt + 1, self.step_id
                        )
                        current_messages.append({"role": "assistant", "content": result["content"]})
                        current_messages.append({
                            "role": "user",
                            "content": f"The code failed with this error:\n\n{execution_output}\n\nPlease fix the code and return the corrected version as JSON."
                        })
                        result = await self.call_llm(
                            current_messages,
                            temperature=0.1,
                            max_tokens=4096,
                            response_format={"type": "json_object"},
                        )
                        output = await self.parse_json_response(result["content"])
                        code = output.get("code", code)
                except Exception as e:
                    output["execution_result"] = f"Sandbox execution failed: {e}"
                    output["success"] = False
                    break

        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

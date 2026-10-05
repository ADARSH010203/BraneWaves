"""
ARC Platform — RepairAgent
Fixes failed steps by analysing errors and generating corrected outputs.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.agent_outputs import RepairOutput
from app.agents.context_utils import compress_dependency_output, truncate_to_tokens


class RepairAgent(BaseAgent):
    """Diagnoses and repairs failed agent steps."""

    agent_type = AgentType.REPAIR
    system_prompt = """You are an expert repair agent. When a step fails, your job is to:
1. Analyse the error message and failed step details
2. Determine the root cause
3. Generate a corrected output that satisfies the step's requirements
4. Explain what went wrong and how you fixed it

Output valid JSON matching the exact required schema.

Rules:
- Always provide a corrected_output
- Be honest about confidence levels
- If you can't fix it, set confidence to 0.0 and explain why"""
    temperature = 0.2

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        error = input_data.get("error", "Unknown error")
        step = input_data.get("step", {})

        input_data_dict = step.get('input_data', {})
        if isinstance(input_data_dict, dict):
            compressed_input = await compress_dependency_output(input_data_dict, max_tokens=3000)
        else:
            compressed_input = truncate_to_tokens(str(input_data_dict), max_tokens=800)

        messages = [
            {
                "role": "user",
                "content": f"""A step in the research pipeline has failed. Please diagnose and repair it.

**Step Title:** {step.get('title', 'Unknown')}
**Step Type:** {step.get('step_type', 'Unknown')}
**Step Description:** {step.get('description', 'Unknown')}
**Error:** {error}

**Step Input Data:**
{compressed_input}

**IMPORTANT — Expected Output Format by step type:**
- research: {{ "summary": "...", "key_findings": [...], "citations": [...], "confidence": 0.0-1.0 }}
- data: {{ "datasets_found": [...], "analysis": "...", "statistics": {{}}, "confidence": 0.0-1.0 }}
- code: {{ "code": "...", "explanation": "...", "execution_result": "...", "success": true/false, "confidence": 0.0-1.0 }}
- critique: {{ "confidence": 0.0-1.0, "quality_score": 0.0-1.0, "issues": [...], "verdict": "pass|needs_revision|fail" }}
- report: {{ "title": "...", "summary": "...", "content": "...", "sections": [...], "confidence": 0.0-1.0 }}

Your corrected_output MUST match the format for step type: {step.get('step_type', 'research')}

Analyse the error and provide a repaired output as JSON matching the RepairOutput schema.""",
            }
        ]

        result = await self.call_llm(
            messages,
            temperature=0.2,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        parsed_output = await self.parse_and_validate(result["content"], RepairOutput)
        output = parsed_output.model_dump()

        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

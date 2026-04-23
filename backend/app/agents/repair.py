"""
ARC Platform — RepairAgent
Fixes failed steps by analysing errors and generating corrected outputs.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType


class RepairAgent(BaseAgent):
    """Diagnoses and repairs failed agent steps."""

    agent_type = AgentType.REPAIR
    system_prompt = """You are an expert repair agent. When a step fails, your job is to:
1. Analyse the error message and failed step details
2. Determine the root cause
3. Generate a corrected output that satisfies the step's requirements
4. Explain what went wrong and how you fixed it

Output a JSON object:
{
  "root_cause": "What caused the failure",
  "fix_description": "How you fixed it",
  "corrected_output": { ... },  // The repaired output matching the step's expected format
  "confidence": 0.0-1.0,
  "prevention_suggestion": "How to prevent this in the future"
}

Rules:
- Always provide a corrected_output
- Be honest about confidence levels
- If you can't fix it, set confidence to 0.0 and explain why"""
    temperature = 0.2

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        error = input_data.get("error", "Unknown error")
        step = input_data.get("step", {})

        messages = [
            {
                "role": "user",
                "content": f"""A step in the research pipeline has failed. Please diagnose and repair it.

**Step Title:** {step.get('title', 'Unknown')}
**Step Type:** {step.get('step_type', 'Unknown')}
**Step Description:** {step.get('description', 'Unknown')}
**Error:** {error}

**Step Input Data:**
{str(step.get('input_data', {}))[:3000]}

**IMPORTANT — Expected Output Format by step type:**
- research: {{ "summary": "...", "key_findings": [...], "citations": [...], "confidence": 0.0-1.0 }}
- data: {{ "datasets_found": [...], "analysis": "...", "statistics": {{}}, "confidence": 0.0-1.0 }}
- code: {{ "code": "...", "explanation": "...", "execution_result": "...", "success": true/false, "confidence": 0.0-1.0 }}
- critique: {{ "confidence": 0.0-1.0, "quality_score": 0.0-1.0, "issues": [...], "verdict": "pass|needs_revision|fail" }}
- report: {{ "title": "...", "summary": "...", "content": "...", "sections": [...], "confidence": 0.0-1.0 }}

Your corrected_output MUST match the format for step type: {step.get('step_type', 'research')}

Analyse the error and provide a repaired output as JSON.""",
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

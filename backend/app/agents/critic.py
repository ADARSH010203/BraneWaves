"""
ARC Platform — CriticAgent
Validates outputs from other agents, scores confidence, flags issues.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType


class CriticAgent(BaseAgent):
    """Reviews and validates outputs from other agents."""

    agent_type = AgentType.CRITIC
    system_prompt = """You are a rigorous research critic agent. Your job is to:
1. Review the output from another agent
2. Assess accuracy, completeness, and quality
3. Check citations and claims for validity
4. Assign a confidence score
5. List specific issues that need fixing

Output a JSON object:
{
  "confidence": 0.0-1.0,
  "quality_score": 0.0-1.0,
  "issues": ["issue 1", "issue 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "verdict": "pass|needs_revision|fail",
  "feedback": "Detailed review feedback"
}

Be strict but fair. Focus on:
- Factual accuracy
- Citation quality
- Completeness of analysis
- Logical consistency
- Methodological soundness"""
    temperature = 0.2

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        output_to_review = input_data.get("output_to_review", {})

        messages = [
            {
                "role": "user",
                "content": f"""Review and critique the following research output:

```json
{str(output_to_review)[:6000]}
```

Provide a thorough quality assessment as JSON.""",
            }
        ]

        result = await self.call_llm(
            messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        output = await self.parse_json_response(result["content"])
        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

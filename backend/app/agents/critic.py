"""
ARC Platform — CriticAgent
Validates outputs from other agents, scores confidence, flags issues.
"""
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.agent_outputs import CriticOutput
from app.agents.context_utils import compress_dependency_output, truncate_to_tokens


class CriticAgent(BaseAgent):
    """Reviews and validates outputs from other agents."""

    agent_type = AgentType.CRITIC
    system_prompt = """You are a rigorous research critic agent. Your job is to:
1. Review the output from another agent
2. Assess accuracy, completeness, and quality
3. Check citations and claims for validity
4. Assign a confidence score
5. List specific issues that need fixing

Output valid JSON matching the exact required schema.

Be strict but fair. Focus on:
- Factual accuracy
- Citation quality
- Completeness of analysis
- Logical consistency
- Methodological soundness"""
    temperature = 0.2

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        output_to_review = input_data.get("output_to_review", {})

        compressed_output = ""
        if isinstance(output_to_review, dict):
            compressed_output = await compress_dependency_output(output_to_review, max_tokens=3000)
        else:
            compressed_output = truncate_to_tokens(str(output_to_review), max_tokens=1500)

        messages = [
            {
                "role": "user",
                "content": f"""Review and critique the following research output:

```json
{compressed_output}
```

Provide a thorough quality assessment as JSON matching the CriticOutput schema.""",
            }
        ]

        from app.config import get_settings
        settings = get_settings()

        result = await self.call_llm(
            messages,
            model=settings.FALLBACK_LLM_MODEL,
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        parsed_output = await self.parse_and_validate(result["content"], CriticOutput)
        output = parsed_output.model_dump()

        output["tokens"] = result["tokens"]
        output["cost_usd"] = result["cost_usd"]
        return output

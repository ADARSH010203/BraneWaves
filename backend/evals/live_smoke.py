"""Live credentialed integration smoke checks."""
from __future__ import annotations

import asyncio
import json
import os

from app.agents.llm_client import chat_completion
from app.tools.python_sandbox import PythonSandboxTool


async def main() -> None:
    checks: dict[str, dict] = {}

    response = await chat_completion(
        messages=[{"role": "user", "content": "Reply with exactly: ARC_LLM_OK"}],
        temperature=0,
        max_tokens=32,
    )
    llm_text = (response.choices[0].message.content or "").strip()
    checks["groq_llm"] = {
        "ok": "ARC_LLM_OK" in llm_text,
        "response": llm_text[:120],
    }

    if os.getenv("PYTHON_SANDBOX_URL"):
        sandbox = await PythonSandboxTool().execute(
            {"code": "print(6 * 7)", "timeout": 10},
            "live-smoke",
        )
        checks["python_sandbox"] = {
            "ok": bool(sandbox.get("success") and "42" in sandbox.get("output", "")),
            "error": sandbox.get("error"),
        }
    else:
        checks["python_sandbox"] = {
            "ok": True,
            "skipped": True,
            "reason": (
                "PYTHON_SANDBOX_URL not configured; runtime capability gating "
                "disables CodeAgent steps."
            ),
        }

    print(json.dumps(checks, indent=2))
    failed = [name for name, result in checks.items() if not result.get("ok")]
    if failed:
        raise SystemExit(f"Live integration smoke failed: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())

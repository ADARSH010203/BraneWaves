"""ARC Platform — isolated Python sandbox client.

The API process never executes untrusted Python locally.  Code is forwarded to a
separately deployed sandbox service (container/microVM) that must enforce CPU,
memory, network, filesystem and process limits.  The AST checks below are only
defense in depth; they are not treated as a security boundary.
"""
from __future__ import annotations

import ast
import logging
from typing import Any

import httpx
from pydantic import Field

from app.config import get_settings
from app.tools.base import BaseTool, ToolInput

logger = logging.getLogger("arc.tools.sandbox")
settings = get_settings()

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
    "requests", "signal", "ctypes", "multiprocessing", "pathlib",
    "importlib", "builtins", "code", "codeop", "compileall", "pty",
    "posix", "posixpath", "nt", "ntpath", "platform", "resource",
}

FORBIDDEN_BUILTINS = {
    "eval", "exec", "compile", "__import__", "open", "breakpoint",
    "getattr", "setattr", "delattr", "vars", "globals", "locals",
    "input", "memoryview", "exit", "quit",
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__mro__", "__bases__", "__class__", "__globals__",
    "__code__", "__builtins__", "__import__", "__loader__", "__spec__",
}


class PythonSandboxInput(ToolInput):
    code: str = Field(min_length=1, max_length=10000)
    timeout: int = Field(default=30, ge=1, le=60)


def _validate_code(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    return f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in FORBIDDEN_MODULES:
                return f"Forbidden import: {node.module}"
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRIBUTES:
            return f"Forbidden attribute access: {node.attr}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                return f"Forbidden call: {node.func.id}()"
    return None


class PythonSandboxTool(BaseTool):
    name = "python_sandbox"
    description = "Execute Python in the separately isolated ARC sandbox service"
    input_schema = PythonSandboxInput
    timeout_seconds = 65
    cost_estimate_usd = 0.001
    permission_scope = "elevated"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        code = params["code"]
        timeout = params.get("timeout", 30)

        validation_error = _validate_code(code)
        if validation_error:
            return {"success": False, "error": validation_error, "output": ""}

        if not settings.PYTHON_SANDBOX_URL:
            return {
                "success": False,
                "error": (
                    "Python sandbox is disabled. Configure PYTHON_SANDBOX_URL to "
                    "a separately isolated sandbox service; local execution is forbidden."
                ),
                "output": "",
            }

        headers = {"Content-Type": "application/json"}
        if settings.PYTHON_SANDBOX_API_KEY:
            headers["Authorization"] = f"Bearer {settings.PYTHON_SANDBOX_API_KEY}"

        payload = {
            "code": code,
            "timeout_seconds": timeout,
            "request_user_id": user_id,
            "network": "disabled",
            "filesystem": "ephemeral",
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout + 5.0),
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    settings.PYTHON_SANDBOX_URL.rstrip("/") + "/execute",
                    json=payload,
                    headers=headers,
                )
            response.raise_for_status()
            data = response.json()
            return {
                "success": bool(data.get("success", False)),
                "output": str(data.get("output", ""))[:10000],
                "stderr": str(data.get("stderr", ""))[:5000] or None,
                "return_code": data.get("return_code"),
                "error": data.get("error"),
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Sandbox service timed out after {timeout}s",
                "output": "",
            }
        except Exception as exc:
            logger.exception("Sandbox service request failed")
            return {
                "success": False,
                "error": f"Sandbox service unavailable: {exc}",
                "output": "",
            }

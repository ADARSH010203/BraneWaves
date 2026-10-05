"""
ARC Platform — Python Sandbox Tool
Executes Python code in a restricted subprocess with resource limits.
"""
from __future__ import annotations

import ast
import asyncio
import logging
import textwrap
from typing import Any

from pydantic import Field

from app.config import get_settings
from app.tools.base import BaseTool, ToolInput

logger = logging.getLogger("arc.tools.sandbox")
settings = get_settings()

# ── Forbidden modules for AST-based checking ────────────────────────────────
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
    "requests", "signal", "ctypes", "multiprocessing", "pathlib",
    "importlib", "builtins", "code", "codeop", "compileall",
}

FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__", "open", "breakpoint"}


class PythonSandboxInput(ToolInput):
    """Input schema for Python sandbox."""
    code: str = Field(min_length=1, max_length=10000, description="Python code to execute")
    timeout: int = Field(default=30, ge=1, le=60, description="Execution timeout in seconds")


class PythonSandboxTool(BaseTool):
    """Executes Python code in a restricted environment."""

    name = "python_sandbox"
    description = "Execute Python code in a sandboxed environment for data analysis"
    input_schema = PythonSandboxInput
    timeout_seconds = 60
    cost_estimate_usd = 0.001
    permission_scope = "elevated"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        code = params["code"]
        timeout = params.get("timeout", 30)

        # BUG-07 FIX: AST-based security check instead of string matching
        # This prevents bypasses like "im" + "port os"
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}", "output": ""}

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_root = alias.name.split(".")[0]
                    if mod_root in FORBIDDEN_MODULES:
                        return {
                            "success": False,
                            "error": f"Forbidden import: {alias.name}",
                            "output": "",
                        }
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    mod_root = node.module.split(".")[0]
                    if mod_root in FORBIDDEN_MODULES:
                        return {
                            "success": False,
                            "error": f"Forbidden import: {node.module}",
                            "output": "",
                        }
            # Check dangerous builtins (eval, exec, compile, open, __import__)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                    return {
                        "success": False,
                        "error": f"Forbidden call: {node.func.id}()",
                        "output": "",
                    }

        # Wrap code to capture output
        wrapped = textwrap.dedent(f"""
import json, math, statistics, collections, itertools, functools
import datetime, re, string, decimal, fractions
try:
    import numpy as np
    import pandas as pd
except ImportError:
    pass

_output_lines = []
_original_print = print
def print(*args, **kwargs):
    import io
    buf = io.StringIO()
    _original_print(*args, file=buf, **kwargs)
    _output_lines.append(buf.getvalue())

try:
{textwrap.indent(code, '    ')}
except Exception as e:
    _output_lines.append(f"ERROR: {{type(e).__name__}}: {{e}}")

_original_print("\\n".join(_output_lines))
""")

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-c", wrapped,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

            success = proc.returncode == 0 and "ERROR:" not in stdout_str

            return {
                "success": success,
                "output": stdout_str,
                "stderr": stderr_str if stderr_str else None,
                "return_code": proc.returncode,
            }

        except asyncio.TimeoutError:
            # BUG-04 FIX: Kill zombie process on timeout
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            return {
                "success": False,
                "error": f"Code execution timed out after {timeout}s",
                "output": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
            }

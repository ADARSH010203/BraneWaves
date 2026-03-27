"""
ARC Platform — Python Sandbox Tool
Executes Python code in a restricted subprocess with resource limits.
"""
from __future__ import annotations

import asyncio
import logging
import textwrap
from typing import Any

from pydantic import Field

from app.config import get_settings
from app.tools.base import BaseTool, ToolInput

logger = logging.getLogger("arc.tools.sandbox")
settings = get_settings()

# ── Forbidden imports / statements ───────────────────────────────────────────
FORBIDDEN_PATTERNS = [
    "import os", "import sys", "import subprocess", "import shutil",
    "import socket", "import http", "import urllib", "import requests",
    "__import__", "eval(", "exec(", "compile(", "open(",
    "os.system", "os.popen", "os.exec", "os.spawn",
    "shutil.rmtree", "pathlib.Path", "import pathlib",
    "import signal", "import ctypes", "import multiprocessing",
]


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

        # Security: check for forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in code:
                return {
                    "success": False,
                    "error": f"Forbidden code pattern detected: '{pattern}'",
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

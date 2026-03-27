"""Tests for tools — base tool, registry, and individual tools."""
import pytest
from app.tools.base import BaseTool, ToolInput
from app.tools.registry import ToolRegistry
from app.tools.web_search import WebSearchTool, WebSearchInput
from app.tools.paper_search import PaperSearchTool
from app.tools.dataset_search import DatasetSearchTool
from app.tools.python_sandbox import PythonSandboxTool, FORBIDDEN_PATTERNS
from app.tools.citation_verify import CitationVerifyTool


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = WebSearchTool()
        reg.register(tool)
        assert reg.get("web_search") is not None
        assert reg.get("nonexistent") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        reg.register(PaperSearchTool())
        tools = reg.list_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "web_search" in names
        assert "paper_search" in names

    def test_allowlist(self):
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        assert reg.is_allowed("web_search") is True
        reg.set_allowlist(["paper_search"])
        assert reg.is_allowed("web_search") is False


class TestToolInputValidation:
    def test_web_search_input(self):
        inp = WebSearchInput(query="test")
        assert inp.query == "test"
        assert inp.num_results == 10

    def test_web_search_input_invalid(self):
        with pytest.raises(Exception):
            WebSearchInput(query="")


class TestPythonSandbox:
    def test_forbidden_patterns(self):
        assert "import os" in FORBIDDEN_PATTERNS
        assert "eval(" in FORBIDDEN_PATTERNS

    @pytest.mark.asyncio
    async def test_safe_code_detection(self):
        tool = PythonSandboxTool()
        result = await tool.execute(
            {"code": "import os\nos.system('rm -rf /')", "timeout": 5}, "u1"
        )
        assert result["success"] is False
        assert "Forbidden" in result.get("error", "")

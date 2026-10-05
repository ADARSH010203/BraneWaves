"""Tests for tools — base tool, registry, and individual tools."""
import pytest
from app.tools.base import BaseTool, ToolInput
from app.tools.registry import ToolRegistry
from app.tools.web_search import WebSearchTool, WebSearchInput
from app.tools.paper_search import PaperSearchTool
from app.tools.dataset_search import DatasetSearchTool
from app.tools.python_sandbox import PythonSandboxTool, FORBIDDEN_MODULES, FORBIDDEN_BUILTINS
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


    @pytest.mark.asyncio
    async def test_elevated_tool_requires_scope(self):
        reg = ToolRegistry()
        reg.register(PythonSandboxTool())
        with pytest.raises(PermissionError):
            await reg.execute(
                "python_sandbox",
                {"code": "print(1)", "timeout": 1},
                "u1",
                allowed_tools={"python_sandbox"},
                granted_scopes={"basic"},
            )

    @pytest.mark.asyncio
    async def test_agent_tool_allowlist_is_enforced(self):
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        with pytest.raises(PermissionError):
            await reg.execute(
                "web_search",
                {"query": "test"},
                "u1",
                allowed_tools={"paper_search"},
                granted_scopes={"basic"},
            )


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
        assert "os" in FORBIDDEN_MODULES
        assert "eval" in FORBIDDEN_BUILTINS

    @pytest.mark.asyncio
    async def test_safe_code_detection(self):
        tool = PythonSandboxTool()
        result = await tool.execute(
            {"code": "import os\nos.system('rm -rf /')", "timeout": 5}, "u1"
        )
        assert result["success"] is False
        assert "Forbidden" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_forbidden_attribute_detection(self):
        tool = PythonSandboxTool()
        result = await tool.execute(
            {"code": "x = ().__class__.__bases__[0].__subclasses__()", "timeout": 5}, "u1"
        )
        assert result["success"] is False
        assert "Forbidden attribute access" in result.get("error", "")


    @pytest.mark.asyncio
    async def test_safe_code_fails_closed_without_isolated_service(self, monkeypatch):
        from app.tools import python_sandbox as sandbox_module
        monkeypatch.setattr(sandbox_module.settings, "PYTHON_SANDBOX_URL", None)
        tool = PythonSandboxTool()
        result = await tool.execute({"code": "print(1)", "timeout": 1}, "u1")
        assert result["success"] is False
        assert "disabled" in result["error"].lower()


class TestCitationVerifySSRF:
    @pytest.mark.asyncio
    async def test_blocks_private_and_metadata_ips(self):
        tool = CitationVerifyTool()
        # Test AWS/GCP metadata IP
        res1 = await tool.execute({"url": "http://169.254.169.254/latest/meta-data/"}, "u1")
        assert res1["success"] is False
        assert "blocked" in res1["error"].lower()

        # Test localhost
        res2 = await tool.execute({"url": "http://127.0.0.1:8000/api/secret"}, "u1")
        assert res2["success"] is False
        assert "blocked" in res2["error"].lower()

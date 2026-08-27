import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import ClassVar

from agent_web_search.models import SearchResponse
from agent_web_search.schema import build_tool_schema


class _HermesContext:
    def register_tool(self, **kwargs):
        self.tool = kwargs


def _load_hermes_adapter():
    root = Path(__file__).parents[1]
    parent = types.ModuleType("hermes_plugins")
    parent.__path__ = []
    sys.modules["hermes_plugins"] = parent
    name = "hermes_plugins.agent_web_search"
    spec = importlib.util.spec_from_file_location(
        name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hermes_adapter_uses_dynamic_core_schema(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ark,brave,ddgs,exa")
    module = _load_hermes_adapter()
    context = _HermesContext()
    module.register(context)
    assert context.tool["name"] == "web_search"
    assert context.tool["override"] is True
    assert context.tool["schema"] == build_tool_schema(["ark", "brave", "ddgs", "exa"])
    properties = context.tool["schema"]["parameters"]["properties"]
    assert properties["providers"]["items"]["enum"] == ["ark", "brave", "ddgs", "exa"]
    assert "grok_search_mode" not in context.tool["schema"]["parameters"]["properties"]


def test_hermes_adapter_exposes_grok_mode_only_when_enabled(monkeypatch):
    monkeypatch.setenv("AGENT_WEB_SEARCH_PROVIDERS", "ark,grok")
    module = _load_hermes_adapter()
    context = _HermesContext()
    module.register(context)
    properties = context.tool["schema"]["parameters"]["properties"]
    assert "grok_search_mode" in properties
    assert properties["providers"]["items"]["enum"] == ["ark", "grok"]


def test_hermes_adapter_uses_shared_all_provider_failure_payload(monkeypatch):
    module = _load_hermes_adapter()
    response = SearchResponse(
        query="latest news",
        providers={},
        failed_provider_errors={"ddgs": "timed out"},
    )

    class Engine:
        enabled_provider_names: ClassVar[list[str]] = ["ddgs"]

        def search(self, _request):
            return response

    monkeypatch.setattr(module, "SearchEngine", Engine)
    context = _HermesContext()
    module.register(context)

    payload = json.loads(context.tool["handler"]({"query": "latest news"}))

    assert payload["error"]["code"] == "all_providers_failed"
    assert payload["error"]["provider_errors"] == {"ddgs": "timed out"}

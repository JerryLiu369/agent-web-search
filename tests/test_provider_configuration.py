from __future__ import annotations

import pytest

from agent_web_search.providers.ark import ArkProvider
from agent_web_search.providers.brave import BraveProvider
from agent_web_search.providers.exa import ExaProvider
from agent_web_search.providers.gemini import GeminiProvider
from agent_web_search.providers.grok import GrokProvider
from agent_web_search.providers.parallel import ParallelProvider
from agent_web_search.providers.perplexity import PerplexityProvider
from agent_web_search.providers.tavily import TavilyProvider
from agent_web_search.providers.you import YouProvider


@pytest.mark.parametrize(
    ("provider_type", "env_name", "kwargs"),
    [
        (ArkProvider, "ARK_API_KEY", {"models": ["model"]}),
        (BraveProvider, "BRAVE_SEARCH_API_KEY", {}),
        (ExaProvider, "EXA_API_KEY", {}),
        (GeminiProvider, "GEMINI_API_KEY", {"models": ["model"]}),
        (GrokProvider, "XAI_API_KEY", {"models": ["model"]}),
        (ParallelProvider, "PARALLEL_API_KEY", {}),
        (PerplexityProvider, "PERPLEXITY_API_KEY", {}),
        (TavilyProvider, "TAVILY_API_KEY", {}),
        (YouProvider, "YDC_API_KEY", {}),
    ],
)
def test_explicit_empty_api_key_does_not_fall_back_to_environment(
    monkeypatch, provider_type, env_name, kwargs
):
    monkeypatch.setenv(env_name, "environment-secret")

    provider = provider_type(api_key="", **kwargs)

    assert provider.api_key == ""


def test_none_api_key_still_reads_environment(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "environment-secret")

    assert BraveProvider(api_key=None).api_key == "environment-secret"

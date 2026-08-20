from __future__ import annotations

from dataclasses import dataclass

from .providers import (
    ArkProvider,
    DDGSProvider,
    ExaProvider,
    GeminiProvider,
    GrokProvider,
    TavilyProvider,
)
from .providers.base import Provider


@dataclass(frozen=True)
class ProviderSpec:
    provider_type: type[Provider]
    description: str
    credential_env: str | None = None


PROVIDER_SPECS = {
    "ark": ProviderSpec(
        ArkProvider,
        "Volcengine ARK web search (Doubao)",
        "ARK_API_KEY",
    ),
    "ddgs": ProviderSpec(DDGSProvider, "DuckDuckGo web search"),
    "exa": ProviderSpec(ExaProvider, "Exa web search"),
    "gemini": ProviderSpec(
        GeminiProvider,
        "Gemini Google Search grounding",
        "GEMINI_API_KEY",
    ),
    "grok": ProviderSpec(
        GrokProvider,
        "Grok web search and X Search",
        "XAI_API_KEY",
    ),
    "tavily": ProviderSpec(
        TavilyProvider,
        "Tavily web search",
        "TAVILY_API_KEY",
    ),
}

DEFAULT_PROVIDER_NAMES = ("ark", "ddgs", "exa")


def create_provider_pool(timeout: float) -> dict[str, Provider]:
    return {
        name: spec.provider_type(timeout=timeout)  # type: ignore[call-arg]
        for name, spec in PROVIDER_SPECS.items()
    }

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .providers import (
    ArkProvider,
    BraveProvider,
    CodexAlphaProvider,
    DDGSProvider,
    DeepSeekProvider,
    ExaProvider,
    GeminiProvider,
    GrokProvider,
    ParallelProvider,
    PerplexityProvider,
    TavilyProvider,
    YouProvider,
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
    "brave": ProviderSpec(
        BraveProvider,
        "Brave Search API",
        "BRAVE_SEARCH_API_KEY",
    ),
    "codex_alpha": ProviderSpec(
        CodexAlphaProvider,
        "Experimental Codex Alpha Search gateway",
        "AGENT_WEB_SEARCH_CODEX_ALPHA_API_KEY",
    ),
    "ddgs": ProviderSpec(DDGSProvider, "DuckDuckGo web search"),
    "deepseek": ProviderSpec(
        DeepSeekProvider,
        "DeepSeek Responses API web search",
        "DEEPSEEK_API_KEY",
    ),
    "exa": ProviderSpec(ExaProvider, "Exa web search", "EXA_API_KEY"),
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
    "parallel": ProviderSpec(
        ParallelProvider,
        "Parallel LLM-optimized web search",
        "PARALLEL_API_KEY",
    ),
    "perplexity": ProviderSpec(
        PerplexityProvider,
        "Perplexity structured Search API",
        "PERPLEXITY_API_KEY",
    ),
    "tavily": ProviderSpec(
        TavilyProvider,
        "Tavily web search",
        "TAVILY_API_KEY",
    ),
    "you": ProviderSpec(
        YouProvider,
        "You.com Search API",
        "YDC_API_KEY",
    ),
}

DEFAULT_PROVIDER_NAMES = ("ddgs", "exa", "parallel")


def create_provider_pool(
    timeout: float, names: Iterable[str] | None = None
) -> dict[str, Provider]:
    """Construct only the requested providers, or all providers by default."""
    if names is not None:
        names = tuple(dict.fromkeys(names))
        unknown = [name for name in names if name not in PROVIDER_SPECS]
        if unknown:
            raise ValueError(
                "AGENT_WEB_SEARCH_PROVIDERS contains unknown provider name(s): "
                + ", ".join(unknown)
                + "; available providers: "
                + ", ".join(PROVIDER_SPECS)
            )
    selected = (
        PROVIDER_SPECS
        if names is None
        else {name: PROVIDER_SPECS[name] for name in names}
    )
    return {
        name: spec.provider_type(timeout=timeout)  # type: ignore[call-arg]
        for name, spec in selected.items()
    }

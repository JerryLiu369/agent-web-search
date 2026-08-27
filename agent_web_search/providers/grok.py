from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt, x_search_date_filters
from .base import Provider

ENDPOINT = "https://api.x.ai/v1/responses"


class GrokProvider(Provider):
    """xAI Responses API with native web_search or x_search."""

    name = "grok"

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self.models = configured_models(
            models=models,
            env_name="AGENT_WEB_SEARCH_GROK_MODELS",
            defaults=["grok-4.6"],
        )
        self._model_pool = RoundRobinModels(self.models)
        self.timeout = timeout

    @staticmethod
    def parse(data: dict, tool_names: list[str] | None = None) -> ProviderResponse:
        names = list(tool_names) if tool_names else ["web_search"]
        answer = ""
        results: list[SearchResult] = []
        searched = False
        for item in data.get("output") or []:
            item_type = item.get("type", "")
            searched |= item_type in {"web_search_call", "x_search_call"} or any(
                name in item_type for name in names
            )
            for content in item.get("content") or []:
                if (
                    content.get("type") in {"output_text", "text"}
                    and content.get("text", "").strip()
                ):
                    answer = content["text"]
                for annotation in content.get("annotations") or []:
                    if annotation.get("type") == "url_citation" and annotation.get(
                        "url"
                    ):
                        results.append(
                            SearchResult(
                                title=annotation.get("title", ""),
                                url=annotation["url"],
                                provider="grok",
                            )
                        )
        if not answer and data.get("output_text"):
            answer = data["output_text"]
        unique = {item.url: item for item in results}
        return ProviderResponse(
            provider="grok",
            answer=answer,
            results=list(unique.values()),
            model=data.get("model", ""),
            searched=searched,
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                model=self.models[0],
                error="XAI_API_KEY is not set",
            )
        model = self._model_pool.next()
        mode = request.grok_search_mode
        if mode not in {"web_search", "x_search", "both"}:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Unsupported grok_search_mode: {mode}",
            )
        tool_names = ["web_search", "x_search"] if mode == "both" else [mode]
        tools = []
        for name in tool_names:
            tool = {"type": name}
            if name == "x_search":
                tool.update(x_search_date_filters(request.time_range))
            tools.append(tool)
        payload = {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": search_prompt(
                        request.query,
                        time_range=request.time_range,
                        max_results=request.max_results,
                        max_keyword=request.max_keyword,
                        search_scope={
                            "web_search": "web",
                            "x_search": "x",
                            "both": "both",
                        }[mode],
                    ),
                }
            ],
            "tools": tools,
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                parsed = self.parse(
                    json.loads(response.read().decode()), list(tool_names)
                )
                parsed.model = model
                return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=(
                    f"Grok HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Grok {type(exc).__name__}: {exc}",
            )

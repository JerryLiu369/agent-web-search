from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt
from .base import Provider

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"


class GeminiProvider(Provider):
    """Gemini Interactions API with the native Google Search tool."""

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.models = configured_models(
            models=models,
            env_name="AGENT_WEB_SEARCH_GEMINI_MODELS",
            defaults=["gemini-3.7-flash"],
        )
        self._model_pool = RoundRobinModels(self.models)
        self.timeout = timeout

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        answer = ""
        citations: list[SearchResult] = []
        searched = False
        for step in data.get("output") or data.get("steps") or []:
            step_type = step.get("type", "")
            searched |= step_type == "google_search_call"
            contents = step.get("content") or []
            if isinstance(contents, dict):
                contents = [contents]
            for content in contents:
                if (
                    content.get("type") in {"text", "output_text"}
                    and content.get("text", "").strip()
                ):
                    answer = content["text"]
                for annotation in content.get("annotations") or []:
                    if annotation.get("type") == "url_citation" and annotation.get(
                        "url"
                    ):
                        citations.append(
                            SearchResult(
                                title=annotation.get("title", ""),
                                url=annotation["url"],
                                provider="gemini",
                            )
                        )
            if step_type in {"model_output", "google_search_result"}:
                searched = True
        unique = {item.url: item for item in citations}
        return ProviderResponse(
            provider="gemini",
            answer=answer,
            citations=list(unique.values()),
            model=data.get("model", ""),
            searched=searched,
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                provider=self.name,
                model=self.models[0],
                error="GEMINI_API_KEY is not set",
            )
        model = self._model_pool.next()
        prompt = search_prompt(
            request.query,
            time_range=request.time_range,
            max_results=request.max_results,
            max_keyword=request.max_keyword,
        )
        payload = {
            "model": model,
            "input": prompt,
            "tools": [{"type": "google_search"}],
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                parsed = self.parse(json.loads(response.read().decode()))
                parsed.model = model
                return parsed
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Gemini HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=model,
                error=f"Gemini {type(exc).__name__}: {exc}",
            )

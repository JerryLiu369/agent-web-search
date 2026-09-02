from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request

from ..model_pool import RoundRobinModels, configured_models
from ..models import ProviderResponse, SearchRequest, SearchResult
from ..prompting import search_prompt
from .base import Provider

# When the first ARK response comes back with a prose answer shorter than
# this, we assume it was truncated mid-sentence and issue one follow-up
# /responses continuation request — which is billed as a second call by the
# upstream. Keep the threshold visible: answers above it are returned as-is.
MIN_ANSWER_CHARS_FOR_CONTINUE = 100

DEFAULT_MODELS = [
    "glm-5-2-260617",
    "doubao-seed-2-1-turbo-260628",
    "deepseek-v4-flash-ga-260731",
]
ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/responses"
CONTINUE_PROMPT = "请基于刚才的搜索结果，给出完整综合回答。"  # noqa: RUF001 - intentional Chinese punctuation


class ArkProvider(Provider):
    name = "ark"

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        timeout: float = 60,
    ):
        self.api_key = api_key or os.getenv("ARK_API_KEY", "")
        self.models = configured_models(
            models=models,
            env_name="AGENT_WEB_SEARCH_ARK_MODELS",
            defaults=DEFAULT_MODELS,
        )
        self._model_pool = RoundRobinModels(self.models)
        self.timeout = timeout

    def _key(self) -> str:
        keys = [
            x.strip() for x in self.api_key.replace("\n", ",").split(",") if x.strip()
        ]
        return random.choice(keys) if keys else ""

    @staticmethod
    def parse(data: dict) -> ProviderResponse:
        output = data.get("output") or []
        messages = [x for x in output if x.get("type") == "message"]
        answer = ""
        results: list[SearchResult] = []
        for message in messages:
            for content in message.get("content") or []:
                if (
                    content.get("type") == "output_text"
                    and (content.get("text") or "").strip()
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
                                provider="ark",
                                description="",
                            )
                        )
        unique = {}
        for item in results:
            unique.setdefault(item.url, item)
        searched = any(
            x.get("type") == "web_search_call" and x.get("status") == "completed"
            for x in output
        )
        return ProviderResponse(
            provider="ark",
            answer=answer,
            results=list(unique.values()),
            model=data.get("model", ""),
            searched=searched,
        )

    def search(self, request: SearchRequest) -> ProviderResponse:
        key = self._key()
        if not key:
            return ProviderResponse(provider=self.name, error="ARK_API_KEY is not set")
        prompt = search_prompt(
            request.query,
            time_range=request.time_range,
            max_results=request.max_results,
        )
        model = self._model_pool.next()
        payload = {
            "model": model,
            "input": [
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
            ],
            "tools": [
                {
                    "type": "web_search",
                    "limit": max(1, min(20, request.max_results)),
                }
            ],
            "max_tool_calls": 2,
            "stream": False,
            "thinking": {"type": "enabled"},
            "reasoning": {"effort": "low"},
            "max_output_tokens": 4096,
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                parsed = self.parse(data)
                if (
                    parsed.searched
                    and len(parsed.answer.strip()) < MIN_ANSWER_CHARS_FOR_CONTINUE
                    and data.get("id")
                ):
                    continued = self._continue(key, data["id"])
                    if continued.answer.strip():
                        parsed.answer = continued.answer
                    if continued.results:
                        unique = {item.url: item for item in parsed.results}
                        unique.update({item.url: item for item in continued.results})
                        parsed.results = list(unique.values())
                    parsed.searched = parsed.searched or continued.searched
                return parsed
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:500]
            return ProviderResponse(
                provider=self.name,
                model=payload["model"],
                error=f"ARK HTTP {exc.code}: {body}",
            )
        except Exception as exc:  # noqa: BLE001 - provider/network errors vary
            return ProviderResponse(
                provider=self.name,
                model=payload["model"],
                error=f"ARK {type(exc).__name__}: {exc}",
            )

    def _continue(self, key: str, response_id: str) -> ProviderResponse:
        payload = {
            "previous_response_id": response_id,
            "input": CONTINUE_PROMPT,
            "stream": False,
            "max_output_tokens": 4096,
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return self.parse(json.loads(response.read().decode()))
        except Exception as exc:  # noqa: BLE001 - fallback must never fail the search
            return ProviderResponse(
                provider=self.name,
                error=f"ARK continuation {type(exc).__name__}: {exc}",
            )

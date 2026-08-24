from __future__ import annotations

import os
from collections.abc import Iterable
from threading import Lock


def configured_models(
    *,
    models: Iterable[str] | None,
    env_name: str,
    defaults: Iterable[str],
) -> list[str]:
    """Resolve models from constructor values, environment, or defaults."""
    if models is not None:
        values = models
    else:
        raw = os.getenv(env_name, "").strip()
        values = raw.replace("\n", ",").split(",") if raw else defaults

    normalized = [str(value).strip() for value in values if str(value).strip()]
    if not normalized:
        raise ValueError(f"{env_name} must contain at least one model")
    return list(dict.fromkeys(normalized))


class RoundRobinModels:
    def __init__(self, models: Iterable[str]):
        self.models = tuple(models)
        if not self.models:
            raise ValueError("models must not be empty")
        self._index = 0
        self._lock = Lock()

    def next(self) -> str:
        with self._lock:
            model = self.models[self._index]
            self._index = (self._index + 1) % len(self.models)
            return model

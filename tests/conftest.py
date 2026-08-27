"""Isolate tests from developer-machine environment variables.

Providers fall back to os.getenv() when constructed without an explicit key,
and engine/config behavior is driven by AGENT_WEB_SEARCH_* variables. Any of
these leaking in from the host environment makes tests machine-dependent.

This autouse fixture clears every provider credential and every
AGENT_WEB_SEARCH_* variable for the whole test session. Tests that need a
variable must set it explicitly (monkeypatch.setenv), which is the pattern
the suite already uses.
"""

from __future__ import annotations

import os

import pytest

_CREDENTIAL_VARS = (
    "ARK_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "EXA_API_KEY",
    "EXA_MCP_URL",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "PARALLEL_API_KEY",
    "PERPLEXITY_API_KEY",
    "TAVILY_API_KEY",
    "YDC_API_KEY",
)

_APP_PREFIX = "AGENT_WEB_SEARCH_"


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith(_APP_PREFIX):
            monkeypatch.delenv(name, raising=False)

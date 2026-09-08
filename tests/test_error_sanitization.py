from __future__ import annotations

from pathlib import Path

import pytest

PROVIDER_FILES = (
    "ark.py",
    "brave.py",
    "codex_alpha.py",
    "ddgs.py",
    "deepseek.py",
    "exa.py",
    "gemini.py",
    "grok.py",
    "parallel.py",
    "perplexity.py",
    "tavily.py",
    "you.py",
    "zhipu_chat_search.py",
    "zhipu_common.py",
    "zhipu_web_search.py",
)


@pytest.mark.parametrize("filename", PROVIDER_FILES)
def test_provider_errors_do_not_include_upstream_details(filename: str):
    text = (
        Path(__file__).parents[1] / "agent_web_search" / "providers" / filename
    ).read_text(encoding="utf-8")

    assert "exc.read()" not in text
    assert "exc.reason" not in text
    assert ": {exc}" not in text

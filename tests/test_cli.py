from __future__ import annotations

import json

import pytest

from agent_web_search import cli
from agent_web_search.models import ProviderResponse, SearchResponse


class _Engine:
    def __init__(self, response: SearchResponse):
        self.response = response
        self.enabled_provider_names = list(
            response.providers or response.failed_provider_errors
        )

    def search(self, _request):
        return self.response


def test_cli_writes_success_json_to_stdout(monkeypatch, capsys):
    response = SearchResponse(
        query="latest news",
        providers={"ddgs": ProviderResponse(provider="ddgs", searched=True)},
    )
    monkeypatch.setattr(cli, "SearchEngine", lambda: _Engine(response))

    exit_code = cli.main(["latest news"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert json.loads(captured.out)["query"] == "latest news"
    assert captured.err == ""


def test_cli_writes_all_provider_failure_to_stderr(monkeypatch, capsys):
    response = SearchResponse(
        query="latest news",
        providers={},
        failed_provider_errors={"ddgs": "timed out"},
    )
    monkeypatch.setattr(cli, "SearchEngine", lambda: _Engine(response))

    exit_code = cli.main(["latest news"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {
            "code": "all_providers_failed",
            "message": (
                "All enabled search providers failed. Check provider "
                "configuration, credentials, quotas, and network access."
            ),
            "provider_errors": {"ddgs": "timed out"},
        },
        "query": "latest news",
    }


def test_cli_exposes_package_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.startswith("agent-web-search ")


def test_cli_rejects_a_provider_that_is_not_enabled(monkeypatch, capsys):
    response = SearchResponse(
        query="latest news",
        providers={"ddgs": ProviderResponse(provider="ddgs", searched=True)},
    )
    monkeypatch.setattr(cli, "SearchEngine", lambda: _Engine(response))

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["latest news", "--provider", "ark"])

    assert exc_info.value.code == 2
    assert "providers are not enabled: ark" in capsys.readouterr().err

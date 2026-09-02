from __future__ import annotations

from pathlib import Path


def test_agent_web_search_skill_has_valid_frontmatter_and_current_cli_contract():
    skill = Path(__file__).parents[1] / "skills" / "agent-web-search" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    frontmatter, body = text.split("---", 2)[1:]

    fields = dict(
        line.split(": ", 1) for line in frontmatter.strip().splitlines() if line
    )
    assert fields["name"] == "agent-web-search"
    assert fields["description"]

    for option in (
        "--provider",
        "--max-results",
        "--time-range",
        "--grok-search-mode",
    ):
        assert option in body
    assert "all_providers_failed" in body
    assert "exit status is `0`" in body
    assert "exits with status `1`" in body
    assert "exit with status `2`" in body

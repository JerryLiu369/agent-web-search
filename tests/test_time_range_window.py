from datetime import datetime, timezone

from agent_web_search.prompting import (
    search_prompt,
    time_range_label,
    time_range_window,
    x_search_date_filters,
)


def test_prompt_includes_resolved_window():
    now = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    prompt = search_prompt("latest AI news", time_range="w", max_results=5)
    assert "the past week" in prompt
    assert "Use no more than 5 sources" in prompt

    assert time_range_label("w", now=now) == "the past week (2026-09-07 to 2026-09-14)"
    assert time_range_label("m", now=now) == "the past month (2026-08-15 to 2026-09-14)"
    assert time_range_label("d", now=now) == "the past 24 hours (2026-09-13 to 2026-09-14)"
    assert time_range_label("y", now=now) == "the past year (2025-09-14 to 2026-09-14)"
    assert time_range_label(None) is None
    assert time_range_label("bogus") is None


def test_window_matches_label_and_x_filters():
    now = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    assert time_range_window("w", now=now) == (now.date().replace(day=7), now.date())
    assert time_range_window(None) is None
    assert time_range_window("bogus") is None

    window = time_range_window("w")
    assert window is not None
    start, end = window
    assert x_search_date_filters("w") == {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
    }
    assert x_search_date_filters(None) == {}
    assert x_search_date_filters("bogus") == {}


def test_scope_prefixes_unchanged():
    assert search_prompt("topic", search_scope="x").startswith("Search X")
    assert search_prompt("topic", search_scope="both").startswith(
        "Search the web and X"
    )
    assert search_prompt("topic").startswith("Search the web")

"""Shared argument validation for the web_search tool (F4/F5/F20)."""

from __future__ import annotations

import pytest

from agent_web_search.validation import MAX_QUERY_LENGTH, validate_web_search_arguments

ENABLED = ["ddgs", "exa", "parallel"]


def test_valid_arguments_produce_no_details():
    assert validate_web_search_arguments({"query": "hello"}, ENABLED) == []
    assert (
        validate_web_search_arguments(
            {
                "query": "hello",
                "max_results": 5,
                "time_range": "w",
                "providers": ["ddgs"],
            },
            ENABLED,
        )
        == []
    )


def test_unknown_fields_are_rejected():
    details = validate_web_search_arguments({"query": "hi", "bogus": 1}, ENABLED)
    assert len(details) == 1
    assert "unknown argument" in details[0]
    assert "bogus" in details[0]


def test_removed_max_keyword_field_is_rejected():
    details = validate_web_search_arguments(
        {"query": "hi", "max_keyword": 2}, ENABLED
    )
    assert len(details) == 1
    assert "max_keyword" in details[0]


@pytest.mark.parametrize("query", ["", "   ", None, 42])
def test_empty_or_non_string_query_is_rejected(query):
    details = validate_web_search_arguments({"query": query}, ENABLED)
    assert len(details) == 1
    assert "query must be a non-empty string" in details[0]


def test_missing_query_is_rejected():
    assert validate_web_search_arguments({}, ENABLED)


@pytest.mark.parametrize("value", ["ten", 1.5, True, 0, 21, -3])
def test_out_of_range_or_non_integer_counts_are_rejected(value):
    details = validate_web_search_arguments(
        {"query": "hi", "max_results": value}, ENABLED
    )
    assert details, f"max_results={value!r} should be rejected"


def test_integer_bounds_are_accepted():
    assert (
        validate_web_search_arguments(
            {"query": "hi", "max_results": 20}, ENABLED
        )
        == []
    )


def test_invalid_time_range_is_rejected():
    details = validate_web_search_arguments(
        {"query": "hi", "time_range": "hour"}, ENABLED
    )
    assert any("time_range" in d for d in details)


def test_string_providers_is_rejected_with_a_hint():
    details = validate_web_search_arguments(
        {"query": "hi", "providers": "ddgs"}, ENABLED
    )
    assert any("providers must be an array" in d and '["ddgs"]' in d for d in details)


def test_empty_providers_list_is_rejected():
    details = validate_web_search_arguments({"query": "hi", "providers": []}, ENABLED)
    assert any("at least one" in d for d in details)


def test_non_string_provider_entries_are_rejected():
    details = validate_web_search_arguments(
        {"query": "hi", "providers": ["ddgs", 5]}, ENABLED
    )
    assert any("must contain strings" in d for d in details)


def test_unknown_provider_is_rejected_with_enabled_list():
    details = validate_web_search_arguments(
        {"query": "hi", "providers": ["nope"]}, ENABLED
    )
    assert any("providers are not enabled: nope" in d and "ddgs" in d for d in details)


def test_invalid_grok_mode_is_rejected():
    details = validate_web_search_arguments(
        {"query": "hi", "grok_search_mode": "turbo"}, [*ENABLED, "grok"]
    )
    assert any("grok_search_mode" in d for d in details)


def test_grok_mode_is_rejected_when_grok_is_not_enabled():
    details = validate_web_search_arguments(
        {"query": "hi", "grok_search_mode": "web_search"}, ENABLED
    )

    assert details == ["grok_search_mode is only available when grok is enabled"]


def test_query_length_is_bounded():
    details = validate_web_search_arguments(
        {"query": "x" * (MAX_QUERY_LENGTH + 1)}, ENABLED
    )

    assert any(f"at most {MAX_QUERY_LENGTH}" in d for d in details)


def test_duplicate_provider_names_are_rejected():
    details = validate_web_search_arguments(
        {"query": "hi", "providers": ["ddgs", "ddgs"]}, ENABLED
    )

    assert "providers must not contain duplicate names" in details


def test_multiple_problems_are_all_reported():
    details = validate_web_search_arguments(
        {"query": "", "providers": "ddgs", "bogus": 1}, ENABLED
    )
    assert len(details) == 3

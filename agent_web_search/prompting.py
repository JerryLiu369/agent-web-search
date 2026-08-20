from __future__ import annotations

from datetime import UTC, datetime, timedelta

TIME_RANGE_LABELS = {
    "d": "the past 24 hours",
    "w": "the past week",
    "m": "the past month",
    "y": "the past year",
}
TIME_RANGE_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


def search_prompt(
    query: str,
    time_range: str | None = None,
    max_results: int | None = None,
    max_keyword: int | None = None,
    search_scope: str = "web",
) -> str:
    """Build an English soft constraint prompt for model-backed search providers."""
    scope_instructions = {
        "web": "Search the web and answer the question using current, verifiable sources.",
        "x": "Search X and answer the question using current, verifiable posts and sources.",
        "both": "Search the web and X and answer the question using current, verifiable sources.",
    }
    constraints = [scope_instructions.get(search_scope, scope_instructions["web"])]
    if time_range in TIME_RANGE_LABELS:
        constraints.append(
            f"Focus on information published within {TIME_RANGE_LABELS[time_range]}."
        )
    if max_results is not None:
        constraints.append(
            f"Use no more than {max_results} sources in the final answer when practical."
        )
    if max_keyword is not None:
        constraints.append(
            f"Use up to {max_keyword} distinct search queries if additional searches are needed."
        )
    return " ".join(constraints) + f"\nQuestion: {query}"


def x_search_date_filters(time_range: str | None) -> dict[str, str]:
    """Translate the common range to xAI X Search's native date filters."""
    if time_range not in TIME_RANGE_DAYS:
        return {}
    today = datetime.now(UTC).date()
    start = today - timedelta(days=TIME_RANGE_DAYS[time_range])
    return {"from_date": start.isoformat(), "to_date": today.isoformat()}

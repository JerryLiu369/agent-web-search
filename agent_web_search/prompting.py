from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

TIME_RANGE_LABELS = {
    "d": "the past 24 hours",
    "w": "the past week",
    "m": "the past month",
    "y": "the past year",
}
TIME_RANGE_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


def time_range_window(
    time_range: str | None, now: datetime | None = None
) -> tuple[date, date] | None:
    """Resolve a common range to the concrete (start, end) dates it covers."""
    if time_range not in TIME_RANGE_DAYS:
        return None
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    return today - timedelta(days=TIME_RANGE_DAYS[time_range]), today


def time_range_label(time_range: str | None, now: datetime | None = None) -> str | None:
    """Human label plus resolved window, e.g. 'the past week (2026-09-07 to 2026-09-14)'.

    Model-backed providers only receive prompt text, so the window has to be
    spelled out in dates — otherwise the model falls back to its own notion of
    'now', which drifts toward its training cutoff.
    """
    if time_range not in TIME_RANGE_LABELS:
        return None
    window = time_range_window(time_range, now=now)
    if window is None:  # pragma: no cover - TIME_RANGE_LABELS/TIME_RANGE_DAYS agree
        return TIME_RANGE_LABELS[time_range]
    start, end = window
    return f"{TIME_RANGE_LABELS[time_range]} ({start.isoformat()} to {end.isoformat()})"


def search_prompt(
    query: str,
    time_range: str | None = None,
    max_results: int | None = None,
    search_scope: str = "web",
) -> str:
    """Build an English soft constraint prompt for model-backed search providers."""
    scope_instructions = {
        "web": (
            "Search the web and answer the question using current, verifiable sources."
        ),
        "x": (
            "Search X and answer the question using current, verifiable "
            "posts and sources."
        ),
        "both": (
            "Search the web and X and answer the question using current, "
            "verifiable sources."
        ),
    }
    constraints = [scope_instructions.get(search_scope, scope_instructions["web"])]
    label = time_range_label(time_range)
    if label is not None:
        constraints.append(f"Focus on information published within {label}.")
    if max_results is not None:
        constraints.append(
            f"Use no more than {max_results} sources in the final answer "
            f"when practical."
        )
    return " ".join(constraints) + f"\nQuestion: {query}"


def x_search_date_filters(time_range: str | None) -> dict[str, str]:
    """Translate the common range to xAI X Search's native date filters."""
    window = time_range_window(time_range)
    if window is None:
        return {}
    start, end = window
    return {"from_date": start.isoformat(), "to_date": end.isoformat()}

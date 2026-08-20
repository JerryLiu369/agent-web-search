from __future__ import annotations

TIME_RANGE_LABELS = {
    "d": "the past 24 hours",
    "w": "the past week",
    "m": "the past month",
    "y": "the past year",
}


def search_prompt(query: str, time_range: str | None = None, max_results: int | None = None, max_keyword: int | None = None) -> str:
    """Build an English soft constraint prompt for model-backed search providers."""
    constraints = [
        "Search the web and answer the question using current, verifiable sources.",
    ]
    if time_range in TIME_RANGE_LABELS:
        constraints.append(f"Focus on information published within {TIME_RANGE_LABELS[time_range]}.")
    if max_results is not None:
        constraints.append(f"Use no more than {max_results} sources in the final answer when practical.")
    if max_keyword is not None:
        constraints.append(f"Use up to {max_keyword} distinct search queries if additional searches are needed.")
    return " ".join(constraints) + f"\nQuestion: {query}"

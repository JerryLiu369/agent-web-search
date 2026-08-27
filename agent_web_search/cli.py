from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .engine import SearchEngine
from .models import SearchRequest
from .output import search_result_payload


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-provider web search for AI agents")
    p.add_argument("query")
    p.add_argument(
        "--version", action="version", version=f"agent-web-search {__version__}"
    )
    p.add_argument("--provider", action="append", dest="providers")
    p.add_argument("--max-results", type=int, default=10)
    p.add_argument("--max-keyword", type=int, default=3)
    p.add_argument("--time-range", choices=["d", "w", "m", "y"])
    p.add_argument(
        "--grok-search-mode",
        choices=["web_search", "x_search", "both"],
        default="web_search",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    p = _parser()
    args = p.parse_args(argv)
    engine = SearchEngine()
    enabled = engine.enabled_provider_names
    if not enabled:
        p.error("no search providers are enabled")
    unavailable = [
        name for name in dict.fromkeys(args.providers or []) if name not in enabled
    ]
    if unavailable:
        p.error(
            "providers are not enabled: "
            + ", ".join(unavailable)
            + "; enabled providers: "
            + ", ".join(enabled)
        )
    try:
        response = engine.search(
            SearchRequest(
                query=args.query,
                max_results=args.max_results,
                max_keyword=args.max_keyword,
                time_range=args.time_range,
                providers=args.providers,
                grok_search_mode=args.grok_search_mode,
            )
        )
    except ValueError as exc:
        p.error(str(exc))
    payload, is_error = search_result_payload(response)
    print(
        json.dumps(payload, ensure_ascii=False, indent=2),
        file=sys.stderr if is_error else sys.stdout,
    )
    return 1 if is_error else 0

from __future__ import annotations

import argparse
import json

from .engine import SearchEngine
from .models import SearchRequest


def main():
    p = argparse.ArgumentParser(description="Multi-provider web search for AI agents")
    p.add_argument("query")
    p.add_argument("--provider", action="append", dest="providers")
    p.add_argument("--max-results", type=int, default=10)
    p.add_argument("--time-range", choices=["d", "w", "m", "y"])
    args = p.parse_args()
    response = SearchEngine().search(
        SearchRequest(
            query=args.query,
            max_results=args.max_results,
            time_range=args.time_range,
            providers=args.providers,
        )
    )
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))

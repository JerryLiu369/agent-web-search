"""Agent Web Search: multi-provider web search for AI agents."""

# Defined before subpackage imports so modules reachable from `engine`
# (e.g. providers/parallel.py) can fall back to it without a circular import.
__version__ = "0.7.3"

from .engine import SearchEngine
from .models import SearchRequest, SearchResponse, SearchResult

__all__ = ["SearchEngine", "SearchRequest", "SearchResponse", "SearchResult"]

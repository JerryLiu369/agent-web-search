"""Agent Web Search: multi-provider web search for AI agents."""

from .engine import SearchEngine
from .models import SearchRequest, SearchResponse, SearchResult

__all__ = ["SearchEngine", "SearchRequest", "SearchResponse", "SearchResult"]
__version__ = "0.2.0"

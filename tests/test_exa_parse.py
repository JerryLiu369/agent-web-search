from agent_web_search.providers.exa import ExaProvider


def test_exa_parser_preserves_multiline_highlights():
    text = """Title: Example
URL: https://example.com
Published: 2026-08-20
Author: Example Author
Highlights:
First line
Second line

---

Title: Other
URL: https://other.example
Highlights: Inline summary
"""
    results = ExaProvider.parse_text(text)
    assert len(results) == 2
    assert results[0].description == "First line Second line"
    assert results[0].published_at == "2026-08-20"
    assert results[1].description == "Inline summary"

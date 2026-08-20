from agent_web_search.providers.gemini import GeminiProvider
from agent_web_search.providers.grok import GrokProvider


def test_gemini_parse_citations():
    result = GeminiProvider.parse({
        "model": "gemini-test",
        "output": [
            {"type": "google_search_call"},
            {"type": "model_output", "content": [{
                "type": "text", "text": "answer",
                "annotations": [{"type": "url_citation", "url": "https://example.com", "title": "Example"}],
            }]},
        ],
    })
    assert result.searched and result.answer == "answer"
    assert result.citations[0].url == "https://example.com"


def test_grok_parse_web_and_x_search_calls():
    result = GrokProvider.parse({
        "model": "grok-test",
        "output": [
            {"type": "x_search_call"},
            {"type": "message", "content": [{
                "type": "output_text", "text": "answer",
                "annotations": [{"type": "url_citation", "url": "https://x.com/post", "title": "X"}],
            }]},
        ],
    }, "x_search")
    assert result.searched and result.answer == "answer"
    assert result.citations[0].url == "https://x.com/post"
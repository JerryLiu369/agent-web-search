from agent_web_search.prompting import search_prompt, x_search_date_filters
from agent_web_search.providers.gemini import GeminiProvider
from agent_web_search.providers.grok import GrokProvider
from agent_web_search.schema import build_tool_schema


def test_schema_only_exposes_grok_option_when_enabled():
    default_schema = build_tool_schema(["ark", "ddgs", "exa"])
    grok_schema = build_tool_schema(["ark", "grok"])
    assert "grok_search_mode" not in default_schema["parameters"]["properties"]
    assert "grok_search_mode" in grok_schema["parameters"]["properties"]
    assert "Volcengine ARK web search (Doubao)" in default_schema["description"]
    assert "ark" not in default_schema["description"]
    assert "Failed providers are omitted" in default_schema["description"]
    assert "tool error" in default_schema["description"]


def test_new_search_providers_appear_in_dynamic_schema():
    schema = build_tool_schema(["parallel", "perplexity", "you"])
    providers = schema["parameters"]["properties"]["providers"]["items"]["enum"]

    assert providers == ["parallel", "perplexity", "you"]
    assert "Parallel LLM-optimized web search" in schema["description"]
    assert "Perplexity structured Search API" in schema["description"]
    assert "You.com Search API" in schema["description"]


def test_model_provider_prompt_adapts_common_search_controls():
    prompt = search_prompt(
        "latest AI news", time_range="w", max_results=5, max_keyword=2
    )
    assert "the past week" in prompt
    assert "no more than 5 sources" in prompt
    assert "up to 2 distinct search queries" in prompt


def test_model_provider_prompt_tracks_search_scope():
    assert search_prompt("topic", search_scope="x").startswith("Search X")
    assert search_prompt("topic", search_scope="both").startswith(
        "Search the web and X"
    )


def test_x_search_time_range_uses_native_date_filters():
    filters = x_search_date_filters("w")
    assert set(filters) == {"from_date", "to_date"}
    assert filters["from_date"] < filters["to_date"]
    assert x_search_date_filters(None) == {}


def test_gemini_parse_results():
    result = GeminiProvider.parse(
        {
            "model": "gemini-test",
            "output": [
                {"type": "google_search_call"},
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": "answer",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com",
                                    "title": "Example",
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    )
    assert result.searched and result.answer == "answer"
    assert result.results[0].url == "https://example.com"


def test_grok_parse_web_and_x_search_calls():
    result = GrokProvider.parse(
        {
            "model": "grok-test",
            "output": [
                {"type": "x_search_call"},
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "answer",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://x.com/post",
                                    "title": "X",
                                }
                            ],
                        }
                    ],
                },
            ],
        },
        "x_search",
    )
    assert result.searched and result.answer == "answer"
    assert result.results[0].url == "https://x.com/post"

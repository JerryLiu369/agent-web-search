from agent_web_search.providers.ark import ArkProvider


def test_ark_uses_last_message_and_deduplicates_results():
    result = ArkProvider.parse(
        {
            "model": "m",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "placeholder",
                            "annotations": [
                                {"type": "url_citation", "url": "https://x"}
                            ],
                        }
                    ],
                },
                {"type": "web_search_call", "status": "completed"},
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "final",
                            "annotations": [
                                {"type": "url_citation", "url": "https://x"},
                                {"type": "url_citation", "url": "https://y"},
                            ],
                        }
                    ],
                },
            ],
        }
    )
    assert result.answer == "final"
    assert [x.url for x in result.results] == ["https://x", "https://y"]
    assert result.searched

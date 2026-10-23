"""Optional web search should not require credentials during agent registration."""

from types import SimpleNamespace
from unittest.mock import Mock

from agents.agent_registry.searcher_agent.tools_impl import openai_web_search_tool as search


def test_client_is_created_only_for_a_nonempty_search(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(
        return_value=SimpleNamespace(output_text="Result", output=[]),
    )))
    constructor = Mock(return_value=client)
    monkeypatch.setattr(search, "OpenAI", constructor)
    engine = search.OpenAIWebSearchEngine()
    engine.run("")
    constructor.assert_not_called()
    engine.run("First search")
    engine.run("Second search")
    constructor.assert_called_once_with()
    assert client.responses.create.call_count == 2

"""Tests for pipeline nodes (mocked LLM)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nodes import retrieve_kb, generate
from pipeline.states import CrisisState


def _base_state(**overrides) -> CrisisState:
    s: CrisisState = {
        "messages": [],
        "query": "що робити при загрозі?",
        "kb_context": "",
        "web_context": "",
        "reply": "",
        "session_id": "test",
    }
    s.update(overrides)
    return s


def _mock_client(content: str):
    """Return a mock httpx.Client context manager whose .post() returns a fake response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock_resp.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.return_value = mock_resp
    return mock_client_instance


def test_retrieve_kb_returns_kb_context(tmp_path):
    from knowledge_base import retrieval
    md = tmp_path / "t.md"
    md.write_text("# T\n\n## Розділ\nТекст про загрозу.\n", encoding="utf-8")
    retrieval.init(tmp_path)

    state = _base_state(query="загроза")
    result = retrieve_kb(state)
    assert "kb_context" in result
    assert isinstance(result["kb_context"], str)


def test_generate_calls_llm_and_returns_reply():
    state = _base_state(kb_context="[База знань]\nТекст про евакуацію.\n")
    mock_client_instance = _mock_client("Негайно евакуюйтесь!")

    with patch("pipeline.nodes.httpx.Client", return_value=mock_client_instance):
        result = generate(state)

    assert result["reply"] == "Негайно евакуюйтесь!"
    assert len(result["messages"]) == 2
    call_json = mock_client_instance.post.call_args[1]["json"]
    user_msg = next(m for m in call_json["messages"] if m["role"] == "user")
    assert "евакуацію" in user_msg["content"]
    assert "що робити при загрозі?" in user_msg["content"]


def test_generate_includes_history():
    history = [
        {"type": "human", "content": "перший запит"},
        {"type": "ai", "content": "перша відповідь"},
    ]
    state = _base_state(messages=history, kb_context="")
    mock_client_instance = _mock_client("ok")

    with patch("pipeline.nodes.httpx.Client", return_value=mock_client_instance):
        generate(state)

    msgs = mock_client_instance.post.call_args[1]["json"]["messages"]
    roles = [m["role"] for m in msgs]
    assert "user" in roles or "human" in roles


def test_generate_offline_fallback():
    """When LLM raises, _format_offline is returned instead of crashing."""
    state = _base_state(kb_context="Якийсь контекст.")
    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.post.side_effect = Exception("connection refused")

    with patch("pipeline.nodes.httpx.Client", return_value=mock_client_instance):
        result = generate(state)

    assert result["reply"]  # not empty
    assert "101" in result["reply"] or "офлайн" in result["reply"].lower() or "112" in result["reply"]

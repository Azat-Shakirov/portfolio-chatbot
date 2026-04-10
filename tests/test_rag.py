# tests/test_rag.py
from unittest.mock import MagicMock, patch
from app.rag import build_prompt, retrieve_chunks
from app.prompts import SYSTEM_PROMPT_CORE, PERSONALITY_MODIFIERS, CONTEXT_TEMPLATE


def test_build_prompt_includes_system_core():
    system, user = build_prompt("What is Azat's experience?", ["chunk1", "chunk2"], "casual")
    assert SYSTEM_PROMPT_CORE in system


def test_build_prompt_includes_personality_modifier():
    system, _ = build_prompt("question", ["chunk"], "professional")
    assert PERSONALITY_MODIFIERS["professional"] in system


def test_build_prompt_wraps_chunks_in_context_delimiters():
    system, _ = build_prompt("question", ["my chunk"], "casual")
    assert "[CONTEXT START]" in system
    assert "[CONTEXT END]" in system
    assert "my chunk" in system


def test_build_prompt_returns_user_message_unchanged():
    question = "Tell me about Azat's skills."
    _, user = build_prompt(question, ["chunk"], "casual")
    assert user == question


def test_build_prompt_unknown_personality_falls_back_to_casual():
    system, _ = build_prompt("q", ["c"], "nonexistent_mode")
    assert PERSONALITY_MODIFIERS["casual"] in system


def test_build_prompt_all_valid_personalities():
    for mode in ["casual", "azat", "professional", "wildcard"]:
        system, _ = build_prompt("q", ["c"], mode)
        assert PERSONALITY_MODIFIERS[mode] in system


def test_retrieve_chunks_returns_page_content(monkeypatch):
    mock_doc = MagicMock()
    mock_doc.page_content = "Azat worked at XYZ"
    mock_vs = MagicMock()
    mock_vs.similarity_search.return_value = [mock_doc, mock_doc, mock_doc]
    monkeypatch.setattr("app.rag._vectorstore", mock_vs)

    chunks = retrieve_chunks("work experience")
    assert len(chunks) == 3
    assert chunks[0] == "Azat worked at XYZ"


def test_retrieve_chunks_default_k_is_3(monkeypatch):
    mock_doc = MagicMock()
    mock_doc.page_content = "content"
    mock_vs = MagicMock()
    mock_vs.similarity_search.return_value = [mock_doc] * 3
    monkeypatch.setattr("app.rag._vectorstore", mock_vs)

    retrieve_chunks("question")
    mock_vs.similarity_search.assert_called_once_with("question", k=3)

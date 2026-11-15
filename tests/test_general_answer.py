"""General answers stay direct and cite only evidence actually used."""

from unittest.mock import AsyncMock, Mock
import sys
from types import SimpleNamespace

import config
from core.general_answer import (answer_general, general_prompt,
                                 is_explicit_book_request, needs_web_search)
from core.query_engine import QueryEngine
from core.query_spelling import repair_book_typos


def _finish(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as finished:
        return finished.value
    raise AssertionError("Mocked coroutine unexpectedly yielded")


def test_general_question_intent_and_prompt():
    question = repair_book_typos("how lng it takes to get over a hbit?")
    assert question == "how long it takes to get over a habit?"
    assert needs_web_search(question)
    assert not is_explicit_book_request("According to research, how long does it take?")
    assert is_explicit_book_request("According to the book, how long does it take?")
    prompt = general_prompt(question, [], "A book excerpt about repetition.")
    assert "Answer the actual question directly" in prompt[0]["content"]
    assert "do not lead with or dwell on what a book does not say" in prompt[0]["content"]


def test_outside_books_uses_general_answer_without_retrieval(monkeypatch):
    monkeypatch.setattr("core.general_answer.search_web", AsyncMock(return_value=[]))
    llm = Mock()
    llm.is_available = AsyncMock(return_value=True)
    llm.generate = AsyncMock(return_value="Paris is the capital of France.")
    retriever, reranker, expander = Mock(), Mock(), Mock()
    result = _finish(QueryEngine(retriever, reranker, llm, expander).query(
        "What is the capital of France?"))
    assert result["answer"] == "Paris is the capital of France."
    assert result["query_type"] == "general"
    assert result["sources"] == []
    retriever.retrieve.assert_not_called()
    reranker.rerank.assert_not_called()
    llm.generate.assert_awaited_once()


def test_habit_duration_uses_web_evidence_without_unrelated_book_citation(monkeypatch):
    web = {"kind": "web", "index": 1, "title": "Habit research",
           "url": "https://example.org/habits", "text_preview": "Duration varies."}
    monkeypatch.setattr("core.query_engine.search_web", AsyncMock(return_value=[web]))
    chunk = {"chunk_id": "chunk_123", "text": "Repetition builds habits.",
             "metadata": {"chapter": "Chapter 6", "page_start": 63, "page_end": 64}}
    retriever, reranker, llm = Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [chunk]
    reranker.rerank.return_value = [chunk]
    llm.is_available = AsyncMock(return_value=True)
    llm.generate = AsyncMock(return_value="There is no fixed timeline; it varies [1].")
    engine = QueryEngine(retriever, reranker, llm, Mock(), "subconscious_mind")
    engine._try_expand = AsyncMock(return_value=["how long does it take to get over a habit?"])
    result = _finish(engine.query("how lng it takes to get over a hbit?"))
    assert result["answer"] == "There is no fixed timeline; it varies [1]."
    assert result["sources"] == [web]
    assert "Web results" in llm.generate.call_args.args[0][1]["content"]
    assert "how long it takes to get over a habit?" in llm.generate.call_args.args[0][1]["content"]


def test_web_search_can_be_disabled_without_new_key(monkeypatch):
    from core.web_search import search_web

    monkeypatch.setattr(config, "WEB_SEARCH_ENABLED", False)
    assert _finish(search_web("habit duration")) == []


def test_web_search_keeps_only_public_links_with_snippets(monkeypatch):
    from core.web_search import _search

    class FakeDDGS:
        def __init__(self, timeout):
            assert timeout == 5

        def text(self, question, max_results):
            assert question == "habit duration"
            assert max_results == 4
            return [
                {"title": "Private", "href": "http://localhost/private", "body": "skip"},
                {"title": "Script", "href": "javascript:alert(1)", "body": "skip"},
                {"title": "Empty", "href": "https://example.org/empty", "body": ""},
                {"title": "Study", "href": "https://example.org/study", "body": "Habits vary."},
            ]

    monkeypatch.setitem(sys.modules, "ddgs", SimpleNamespace(DDGS=FakeDDGS))
    assert _search("habit duration") == [{
        "kind": "web", "index": 1, "title": "Study",
        "url": "https://example.org/study", "text_preview": "Habits vary.",
    }]

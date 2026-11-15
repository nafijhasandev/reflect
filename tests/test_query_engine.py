"""Tests for the query pipeline and its failure paths."""

from unittest.mock import AsyncMock, Mock, call

import pytest

import config
from core.query_engine import QueryEngine, _extract_sources
from core.social_reply import social_reply


def _chunk(chunk_id: str, text: str, page: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {
            "chapter": "Chapter 3: How to Build Better Habits",
            "page_start": page,
            "page_end": page,
        },
        "rerank_score": 0.9,
    }


def test_source_ids_match_chunk_snapshot_for_pdf_highlighting():
    source = _extract_sources([_chunk("chunk_a1b2c3d4e5f6_1", "Source text", 25)],
                              "emotional_intelligence")[0]
    assert source["chunk_id"] == "a1b2c3d4e5f6_1"
    assert source["book"] == "emotional_intelligence"


@pytest.mark.parametrize(
    ("message", "prefix"),
    [
        ("Hi!", "Hello!"),
        ("hello there", "Hello!"),
        ("helllo", "Hello!"),
        ("good morning", "Hello!"),
        ("Thank you so much.", "You're welcome!"),
        ("please", "Of course."),
    ],
)
def test_standalone_courtesy_gets_an_invitation(message, prefix):
    reply = social_reply(message, "tiny_habits")
    assert reply.startswith(prefix)
    assert reply.endswith("What would you like to know?")


@pytest.mark.parametrize("message", [
    "Please explain habit stacking.",
    "Hi, what is an anchor moment?",
    "What is the capital of France?",
])
def test_real_questions_do_not_become_social_replies(message):
    assert social_reply(message) is None


def test_social_query_skips_retrieval_and_generation():
    def finish_immediate(coroutine):
        try:
            coroutine.send(None)
        except StopIteration as finished:
            return finished.value
        raise AssertionError("Social replies must not await the RAG pipeline")

    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    engine = QueryEngine(retriever, reranker, llm_client, query_expander, "tiny_habits")

    result = finish_immediate(engine.query("hello"))
    stream = engine.query_stream("thank you")
    events = [finish_immediate(stream.__anext__()) for _ in range(4)]

    assert result["query_type"] == "social"
    assert result["sources"] == []
    assert "What would you like to know?" in result["answer"]
    assert [event["type"] for event in events] == ["metadata", "chunk", "sources", "done"]
    assert events[0]["query_type"] == "social"
    assert events[-1]["answer"].startswith("You're welcome!")
    assert events[2]["sources"] == []
    retriever.retrieve.assert_not_called()
    reranker.rerank.assert_not_called()
    llm_client.is_available.assert_not_called()
    query_expander.expand.assert_not_called()


def test_misspelled_book_question_reaches_corrected_retrieval():
    def finish_immediate(coroutine):
        try:
            coroutine.send(None)
        except StopIteration as finished:
            return finished.value
        raise AssertionError("Mocked query should finish without external calls")

    passage = _chunk("habit", "Small actions can support a new habit.", 42)
    retriever, reranker = Mock(), Mock()
    retriever.retrieve.return_value = [passage]
    reranker.rerank.return_value = [passage]
    engine = QueryEngine(retriever, reranker, Mock(), Mock(), "five_second_rule")
    corrected = "what is the minimum prod to overcome a habit"
    engine._try_expand = AsyncMock(return_value=[corrected])
    engine._try_generate = AsyncMock(return_value="Book-grounded answer (Chapter 3, p.42).")

    result = finish_immediate(engine.query("what is the minimum prod to overcme a hbit"))

    assert result["query_type"] != "out_of_scope"
    assert result["sources"]
    retriever.retrieve.assert_called_once_with(corrected, top_k=config.RERANK_CANDIDATES)
    assert reranker.rerank.call_args.args[0] == corrected
    assert corrected in str(engine._try_generate.call_args.args[0])


def test_misspelled_stream_question_reaches_corrected_retrieval():
    passage = _chunk("habit", "Small actions can support a new habit.", 42)
    retriever, reranker = Mock(), Mock()
    retriever.retrieve.return_value = [passage]
    reranker.rerank.return_value = [passage]
    engine = QueryEngine(retriever, reranker, Mock(), Mock(), "five_second_rule")
    corrected = "what is the minimum prod to overcome a habit"
    engine._try_expand = AsyncMock(return_value=[corrected])

    first_event = engine.query_stream("what is the minimum prod to overcme a hbit").__anext__()
    try:
        first_event.send(None)
    except StopIteration as finished:
        assert finished.value["type"] == "metadata"
        assert finished.value["query_type"] != "out_of_scope"
    else:
        raise AssertionError("Mocked retrieval should finish without external calls")
    retriever.retrieve.assert_called_once_with(corrected, top_k=config.RERANK_CANDIDATES)


@pytest.mark.asyncio
async def test_tiny_habits_query_uses_its_prompt_and_source_book():
    passage = _chunk("tiny", "An anchor moment prompts a tiny behavior.", 23)
    passage["metadata"]["chapter"] = ""
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [passage]
    reranker.rerank.return_value = [passage]
    llm_client.is_available = AsyncMock(return_value=True)
    llm_client.generate = AsyncMock(return_value="Use an anchor moment.")
    query_expander.expand = AsyncMock(return_value=["What is an anchor moment?"])
    engine = QueryEngine(retriever, reranker, llm_client, query_expander, "tiny_habits")

    result = await engine.query("What is an anchor moment?")

    assert result["sources"][0]["book"] == "tiny_habits"
    assert result["answer"] == "Use an anchor moment (p.23)."
    assert "'Tiny Habits' by BJ Fogg" in llm_client.generate.call_args.args[0][0]["content"]


def test_expanded_queries_send_only_top_fifteen_unique_candidates_to_reranker():
    retriever = Mock()
    first = [dict(_chunk(f"first_{index}", "A habit passage.", index + 1), score=0.01)
             for index in range(15)]
    second = [dict(_chunk(f"second_{index}", "Another habit passage.", index + 30), score=0.02)
              for index in range(15)]
    retriever.retrieve.side_effect = [first, second]
    engine = QueryEngine(retriever, Mock(), Mock(), Mock())

    candidates = engine._retrieve_for_queries(["habits", "routines"])

    assert len(candidates) == config.RERANK_CANDIDATES
    assert {candidate["chunk_id"] for candidate in candidates} == {
        f"second_{index}" for index in range(15)
    }


@pytest.mark.asyncio
async def test_query_runs_expansion_retrieval_reranking_and_generation():
    cue = _chunk("cue", "A cue starts the habit loop.", 42)
    stacking = _chunk("stacking", "Habit stacking links a new habit to an existing one.", 43)
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.side_effect = [[cue], [cue, stacking]]
    reranker.rerank.return_value = [stacking, cue]
    llm_client.is_available = AsyncMock(return_value=True)
    llm_client.generate = AsyncMock(return_value="Link the habits (Chapter 3, p.43).")
    query_expander.expand = AsyncMock(return_value=[
        "What is habit stacking?", "link a new habit to an existing one"
    ])
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    result = await engine.query("What is habit stacking?", top_k=2)

    assert result["answer"] == "Link the habits (Chapter 3, p.43)."
    assert [source["chunk_id"] for source in result["sources"]] == ["stacking", "cue"]
    assert result["sources"][0]["metadata"]["page_start"] == 43
    assert result["sources"][0]["chapter"].startswith("Chapter 3")
    assert result["sources"][0]["pages"] == "43-43"
    assert "Habit stacking links" in result["sources"][0]["text"]
    assert result["timing"]["total"] >= 0
    assert retriever.retrieve.call_args_list == [
        call("What is habit stacking?", top_k=config.RERANK_CANDIDATES),
        call(
            "link a new habit to an existing one", top_k=config.RERANK_CANDIDATES
        ),
    ]
    reranker.rerank.assert_called_once()
    rerank_question, rerank_candidates = reranker.rerank.call_args.args
    assert rerank_question == "What is habit stacking?"
    assert [candidate["chunk_id"] for candidate in rerank_candidates] == [
        "cue", "stacking"
    ]
    assert rerank_candidates[0]["score"] > rerank_candidates[1]["score"]
    assert reranker.rerank.call_args.kwargs == {"top_n": 2}
    prompt = llm_client.generate.call_args.args[0]
    assert "Habit stacking links a new habit" in prompt[1]["content"]
    assert "Chapter 3: How to Build Better Habits, Pages 43-43" in prompt[1]["content"]


@pytest.mark.asyncio
async def test_stream_yields_sources_after_answer_and_finishes():
    stacking = _chunk("stacking", "Habit stacking connects two routines.", 43)
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [stacking]
    reranker.rerank.return_value = [stacking]
    llm_client.is_available = AsyncMock(return_value=True)
    query_expander.expand = AsyncMock(return_value=["What is habit stacking?"])

    async def answer_chunks():
        yield "Connect "
        yield "two routines."

    llm_client.generate = AsyncMock(return_value=answer_chunks())
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    events = [event async for event in engine.query_stream("What is habit stacking?")]

    assert [event["type"] for event in events] == [
        "metadata", "chunk", "chunk", "sources", "done"
    ]
    assert events[3]["sources"][0]["chunk_id"] == "stacking"
    assert "".join(event["content"] for event in events[1:3]) == "Connect two routines."
    assert events[-1]["answer"] == "Connect two routines (Chapter 3, p.43)."
    assert events[-1]["timing"]["total"] >= 0
    llm_client.generate.assert_awaited_once()
    assert llm_client.generate.call_args.kwargs == {"stream": True}


@pytest.mark.asyncio
async def test_query_with_no_retrieval_results_skips_reranker_and_generation():
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = []
    llm_client.is_available = AsyncMock(return_value=False)
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    result = await engine.query("What is habit stacking?")

    assert result["sources"] == []
    assert "could not find" in result["answer"]
    reranker.rerank.assert_not_called()
    llm_client.generate.assert_not_called()


@pytest.mark.asyncio
async def test_expansion_failure_uses_original_question():
    stacking = _chunk("stacking", "Habit stacking connects routines.", 43)
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [stacking]
    reranker.rerank.return_value = [stacking]
    llm_client.is_available = AsyncMock(return_value=True)
    llm_client.generate = AsyncMock(return_value="Use an existing routine as a cue.")
    query_expander.expand = AsyncMock(side_effect=RuntimeError("expansion failed"))
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    result = await engine.query("What is habit stacking?")

    assert result["answer"] == (
        "Use an existing routine as a cue (Chapter 3, p.43)."
    )
    retriever.retrieve.assert_called_once_with(
        "What is habit stacking?", top_k=config.RERANK_CANDIDATES
    )


@pytest.mark.asyncio
async def test_unavailable_llm_still_returns_retrieved_sources():
    stacking = _chunk("stacking", "Habit stacking connects routines.", 43)
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [stacking]
    reranker.rerank.return_value = [stacking]
    llm_client.is_available = AsyncMock(return_value=False)
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    result = await engine.query("What is habit stacking?")

    assert "unavailable" in result["answer"]
    assert result["sources"][0]["chunk_id"] == "stacking"
    query_expander.expand.assert_not_called()
    llm_client.generate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "query_type", "expected_top_k"),
    [
        ("What is habit stacking?", "factual", 3),
        ("Why do habits plateau?", "analytical", 5),
        ("Summarize the chapter on habits", "summary", 8),
    ],
)
async def test_query_type_selects_srs_retrieval_depth(
    question: str, query_type: str, expected_top_k: int
):
    chunk = _chunk("habit", "A passage about habits.", 42)
    retriever, reranker, llm_client = Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [chunk]
    reranker.rerank.return_value = [chunk]
    llm_client.is_available = AsyncMock(return_value=False)
    engine = QueryEngine(retriever, reranker, llm_client, Mock())

    result = await engine.query(question)

    assert result["query_type"] == query_type
    assert reranker.rerank.call_args.kwargs["top_n"] == expected_top_k


@pytest.mark.asyncio
async def test_comparison_retrieves_each_subject_separately():
    chunk = _chunk("habit", "A passage about habits.", 42)
    retriever, reranker, llm_client = Mock(), Mock(), Mock()
    retriever.retrieve.return_value = [chunk]
    reranker.rerank.return_value = [chunk]
    llm_client.is_available = AsyncMock(return_value=False)
    engine = QueryEngine(retriever, reranker, llm_client, Mock())
    question = "Compare habit stacking vs. temptation bundling"

    result = await engine.query(question)

    assert result["query_type"] == "comparison"
    assert [item.args[0] for item in retriever.retrieve.call_args_list] == [
        "habit stacking", "temptation bundling", question
    ]
    assert reranker.rerank.call_args.kwargs["top_n"] == 5


def test_unrelated_query_skips_book_pipeline(monkeypatch):
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)
    general = AsyncMock(return_value={
        "answer": "Paris is the capital of France.", "sources": [],
        "query_type": "general", "timing": {"total": 0.0},
    })
    monkeypatch.setattr("core.query_engine.answer_general", general)

    try:
        engine.query("What is the capital of France?").send(None)
    except StopIteration as finished:
        result = finished.value

    assert result["answer"] == "Paris is the capital of France."
    assert result["sources"] == []
    assert result["query_type"] == "general"
    retriever.retrieve.assert_not_called()
    reranker.rerank.assert_not_called()
    llm_client.is_available.assert_not_called()
    query_expander.expand.assert_not_called()
    general.assert_awaited_once()


def test_unrelated_stream_returns_answer_without_retrieval(monkeypatch):
    retriever, reranker, llm_client, query_expander = Mock(), Mock(), Mock(), Mock()
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)
    async def general(question, client):
        assert question == "What is the capital of France?"
        yield {"type": "metadata", "query_type": "general"}
        yield {"type": "chunk", "content": "Paris is the capital of France."}
        yield {"type": "sources", "sources": []}
        yield {"type": "done", "answer": "Paris is the capital of France."}
    monkeypatch.setattr("core.query_engine.answer_general_stream", general)

    stream = engine.query_stream("What is the capital of France?")
    events = []
    for _ in range(4):
        try:
            stream.__anext__().send(None)
        except StopIteration as finished:
            events.append(finished.value)

    assert [event["type"] for event in events] == [
        "metadata", "chunk", "sources", "done"
    ]
    assert events[2]["sources"] == []
    assert events[1]["content"] == "Paris is the capital of France."
    retriever.retrieve.assert_not_called()
    reranker.rerank.assert_not_called()
    llm_client.is_available.assert_not_called()
    query_expander.expand.assert_not_called()


@pytest.mark.asyncio
async def test_generation_error_does_not_reveal_exception():
    chunk = {
        "chunk_id": "chunk_1",
        "text": "A habit starts with a cue.",
        "metadata": {"chapter": "Chapter 3: Habits", "page_start": 42, "page_end": 42},
    }
    retriever = Mock()
    retriever.retrieve.return_value = [chunk]
    reranker = Mock()
    reranker.rerank.return_value = [chunk]
    llm_client = Mock()
    llm_client.is_available = AsyncMock(return_value=True)
    llm_client.generate = AsyncMock(side_effect=RuntimeError("private token"))
    query_expander = Mock()
    query_expander.expand = AsyncMock(return_value=["What is a habit?"])
    engine = QueryEngine(retriever, reranker, llm_client, query_expander)

    events = [event async for event in engine.query_stream("What is a habit?")]

    errors = [event for event in events if event["type"] == "error"]
    assert errors == [
        {"type": "error", "message": "Answer generation failed. Please try again."}
    ]
    assert events[-1]["type"] == "done"

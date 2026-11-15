"""Tests for web query validation and safe streaming errors."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import config
from web import app as web_app


def test_index_serves_chat_page():
    response = TestClient(web_app.app).get("/")

    assert response.status_code == 200
    assert "reflect." in response.text
    assert "/static/reflect-icon.svg" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "/static/stream_events.js?v=" in response.text
    assert "/static/app.js?v=" in response.text
    assert 'class="pdf-native-viewer"' in response.text


def test_book_pdf_serves_configured_file(monkeypatch, tmp_path):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(config, "PDF_PATH", pdf)

    response = TestClient(web_app.app).get("/book.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4"


def test_tiny_habits_pdf_route_uses_its_own_file(monkeypatch, tmp_path):
    pdf = tmp_path / "Tiny Habits.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(config, "TINY_HABITS_PDF_PATH", pdf)

    response = TestClient(web_app.app).get("/book.pdf?book=tiny_habits")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7"


def test_power_of_habit_pdf_route_uses_its_own_file(monkeypatch, tmp_path):
    pdf = tmp_path / "Power of Habit.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(config, "POWER_OF_HABIT_PDF_PATH", pdf)

    response = TestClient(web_app.app).get("/book.pdf?book=power_of_habit")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7"


def test_power_of_now_pdf_route_uses_its_own_file(monkeypatch, tmp_path):
    pdf = tmp_path / "The Power of Now.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    monkeypatch.setattr(config, "POWER_OF_NOW_PDF_PATH", pdf)

    response = TestClient(web_app.app).get("/book.pdf?book=power_of_now")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7"


def test_book_page_image_renders_requested_pdf_page(monkeypatch, tmp_path):
    import pymupdf

    pdf = tmp_path / "book.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "First page")
        document.new_page().insert_text((72, 72), "Second page")
        document.save(pdf)
    monkeypatch.setattr(config, "PDF_PATH", pdf)
    client = TestClient(web_app.app)

    first = client.get("/book-page.png?book=atomic_habits&page=1")
    second = client.get("/book-page.png?book=atomic_habits&page=2")

    assert first.status_code == second.status_code == 200
    assert second.headers["content-type"] == "image/png"
    assert first.content.startswith(b"\x89PNG")
    assert first.content != second.content
    assert client.get("/book-page.png?book=atomic_habits&page=3").status_code == 404


def test_source_page_highlights_matching_passage_and_topic(monkeypatch, tmp_path):
    import pymupdf

    pdf = tmp_path / "book.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "THE HABIT LOOP", fontsize=16)
        page.insert_text((72, 110), "A cue starts a routine and a reward reinforces it.")
        document.save(pdf)
    chunks = tmp_path / "chunks.json"
    chunks.write_text(json.dumps([{
        "chunk_id": "a1b2c3d4e5f6",
        "text": "A cue starts a routine and a reward reinforces it.",
        "chapter": "Chapter 1",
        "section": "THE HABIT LOOP",
        "page_start": 1,
        "page_end": 1,
    }]), encoding="utf-8")
    monkeypatch.setattr(config, "PDF_PATH", pdf)
    monkeypatch.setattr(config, "CHUNKS_JSON_PATH", chunks)
    client = TestClient(web_app.app)

    plain = client.get("/book-page.png?book=atomic_habits&page=1")
    marked = client.get("/book-page.png?book=atomic_habits&page=1&chunk_id=a1b2c3d4e5f6")
    wrong = client.get("/book-page.png?book=atomic_habits&page=1&chunk_id=ffffffffffff")

    assert marked.status_code == 200
    assert int(marked.headers["x-highlighted-words"]) >= 10
    assert marked.content != plain.content
    assert wrong.headers["x-highlighted-words"] == "0"


def test_highlight_covers_full_long_source_passage():
    import pymupdf

    from core.pdf_highlight import highlight_source

    words = [f"term{number}" for number in range(180)]
    with pymupdf.open() as document:
        page = document.new_page()
        text = " ".join(words)
        assert page.insert_textbox(pymupdf.Rect(50, 50, 550, 750), text,
                                   fontsize=10) >= 0

        marked = highlight_source(page, {"text": text, "section": ""})

    assert marked == len(words)


def test_highlight_ignores_short_incidental_match_from_a_long_passage():
    import pymupdf

    from core.pdf_highlight import highlight_source

    fragment = "that rewards satisfy your craving to"
    full_passage = " ".join(f"term{number}" for number in range(120)) + " " + fragment
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), fragment)
        marked = highlight_source(page, {"text": full_passage, "section": ""})

    assert marked == 0


def test_highlighted_source_pdf_opens_best_matching_page(monkeypatch, tmp_path):
    import pymupdf

    pdf = tmp_path / "book.pdf"
    passage = "A cue begins the routine and the reward strengthens the habit loop."
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "THE HABIT LOOP")
        document.new_page().insert_text((72, 72), passage)
        document.save(pdf)
    chunks = tmp_path / "chunks.json"
    chunks.write_text(json.dumps([{
        "chunk_id": "a1b2c3d4e5f6", "text": passage,
        "chapter": "Chapter 1", "section": "THE HABIT LOOP",
        "page_start": 1, "page_end": 2,
    }]), encoding="utf-8")
    monkeypatch.setattr(config, "PDF_PATH", pdf)
    monkeypatch.setattr(config, "CHUNKS_JSON_PATH", chunks)

    client = TestClient(web_app.app)
    response = client.get("/source-page.pdf?book=atomic_habits&chunk_id=a1b2c3d4e5f6")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-original-pdf-page"] == "2"
    assert response.headers["x-original-pdf-pages"] == "2,1"
    with pymupdf.open(stream=response.content, filetype="pdf") as marked_pdf:
        assert len(marked_pdf) == 2
        assert "reward strengthens" in marked_pdf[0].get_text()
        assert list(marked_pdf[0].annots())
    assert client.get("/source-page.pdf?book=atomic_habits&chunk_id=ffffffffffff").status_code == 404


def test_question_answer_source_highlights_only_answer_text():
    import pymupdf

    from core.pdf_highlight import highlight_source

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "How can Action Prompts enhance habit formation?")
        page.insert_text((72, 110),
                         "Answer:Action Prompts leverage existing routines to trigger new habits.")
        chunk = {
            "text": "Question: How can Action Prompts enhance habit formation?\n"
                    "Answer: Action Prompts leverage existing routines to trigger new habits.",
            "section": "How can Action Prompts enhance habit formation?",
        }

        marked = highlight_source(page, chunk)
        annotation_rects = [annotation.rect for annotation in page.annots()]

    assert marked >= 8
    assert annotation_rects
    assert all(rect.y0 > 90 for rect in annotation_rects)
    assert min(rect.x0 for rect in annotation_rects) <= 72


def test_health_reports_configured_hosted_model(monkeypatch):
    monkeypatch.setattr(web_app, "_llm_client", SimpleNamespace(
        is_available=AsyncMock(return_value=True)
    ))
    monkeypatch.setattr(web_app, "_engine", object())
    monkeypatch.setattr(web_app, "VectorStore", lambda: SimpleNamespace(count=lambda: 4))

    response = TestClient(web_app.app).get("/api/health")

    assert response.json() == {
        "status": "ok",
        "llm_configured": True,
        "index_loaded": True,
        "chunk_count": 4,
    }


def test_query_request_trims_question_and_accepts_upper_top_k():
    request = web_app.QueryRequest(
        question="  What is habit stacking?  ", top_k=config.RERANK_CANDIDATES
    )

    assert request.question == "What is habit stacking?"
    assert request.top_k == config.RERANK_CANDIDATES


def test_omitted_top_k_uses_query_type_default():
    request = web_app.QueryRequest(question="What is habit stacking?")

    assert request.top_k is None


def test_query_stream_sends_sources_after_answer(monkeypatch):
    async def stream(question, top_k):
        assert question == "What is habit stacking?"
        assert top_k is None
        yield {"type": "metadata", "query_type": "factual"}
        yield {"type": "chunk", "content": "Habit stacking links routines."}
        yield {"type": "sources", "sources": [{"chapter": "Chapter 5"}]}
        yield {"type": "done", "answer": "Habit stacking links routines (Chapter 5, p.73)."}

    monkeypatch.setattr(web_app, "_engine", SimpleNamespace(query_stream=stream))

    response = TestClient(web_app.app).post(
        "/api/query", json={"question": "What is habit stacking?"}
    )

    events = [json.loads(line.removeprefix("data: "))
              for line in response.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == [
        "metadata", "chunk", "sources", "done"
    ]
    assert events[-1]["answer"].endswith("(Chapter 5, p.73).")


def test_query_routes_tiny_habits_to_its_engine(monkeypatch):
    async def stream(question, top_k):
        assert question == "What is an anchor moment?"
        yield {"type": "done", "answer": "A prompt (p.23)."}

    monkeypatch.setitem(web_app._engines, "tiny_habits", SimpleNamespace(query_stream=stream))
    response = TestClient(web_app.app).post("/api/query", json={
        "question": "What is an anchor moment?", "book": "tiny_habits",
    })

    assert '"answer": "A prompt (p.23)."' in response.text


def test_query_routes_power_of_habit_to_its_engine(monkeypatch):
    async def stream(question, top_k):
        assert question == "What is the habit loop?"
        yield {"type": "done", "answer": "Cue, routine, reward (Chapter 1, p.21)."}

    monkeypatch.setitem(web_app._engines, "power_of_habit", SimpleNamespace(query_stream=stream))
    response = TestClient(web_app.app).post("/api/query", json={
        "question": "What is the habit loop?", "book": "power_of_habit",
    })

    assert response.status_code == 200
    assert '"answer": "Cue, routine, reward (Chapter 1, p.21)."' in response.text


def test_auto_query_announces_selected_book_and_uses_its_engine(monkeypatch):
    async def stream(question, top_k):
        assert question == "What are keystone habits?"
        yield {"type": "sources", "sources": [{"book": "power_of_habit"}]}
        yield {"type": "done", "answer": "A keystone habit."}

    monkeypatch.setattr(web_app, "choose_book", lambda question, engines, reranker: "power_of_habit")
    monkeypatch.setitem(web_app._engines, "power_of_habit", SimpleNamespace(query_stream=stream))
    response = TestClient(web_app.app).post("/api/query", json={
        "question": "What are keystone habits?", "book": "auto",
    })
    events = [json.loads(line.removeprefix("data: "))
              for line in response.text.splitlines() if line.startswith("data: ")]

    assert response.status_code == 200
    assert events[0] == {"type": "book_selected", "book": "power_of_habit"}
    assert events[1]["sources"][0]["book"] == "power_of_habit"
    assert events[-1]["answer"] == "A keystone habit."


def test_auto_greeting_skips_book_selection(monkeypatch):
    def finish_immediate(coroutine):
        try:
            coroutine.send(None)
        except StopIteration as finished:
            return finished.value
        raise AssertionError("A greeting must not await book selection")

    def should_not_route(*args):
        raise AssertionError("A greeting must not search books")

    monkeypatch.setattr(web_app, "choose_book", should_not_route)
    response = finish_immediate(web_app.query_endpoint(
        web_app.QueryRequest(question="Hello!", book="auto")
    ))
    events = [json.loads(finish_immediate(response.body_iterator.__anext__())
                         .removeprefix("data: ")) for _ in range(4)]

    assert [event["type"] for event in events] == ["metadata", "chunk", "sources", "done"]
    assert events[0]["query_type"] == "social"
    assert events[2]["sources"] == []
    assert events[-1]["answer"].startswith("Hello!")


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "   "},
        {"question": "x" * 1001},
        {"question": "Valid?", "top_k": 0},
        {"question": "Valid?", "top_k": config.RERANK_CANDIDATES + 1},
        {"question": "Valid?", "top_k": "5"},
        {"question": "Valid?", "top_k": True},
    ],
)
def test_invalid_query_returns_422(payload):
    response = TestClient(web_app.app).post("/api/query", json=payload)

    assert response.status_code == 422


def test_unexpected_stream_error_hides_exception(monkeypatch):
    async def failing_stream(question, top_k):
        raise RuntimeError("private token and file path")
        yield {}

    monkeypatch.setattr(
        web_app, "_engine", SimpleNamespace(query_stream=failing_stream)
    )

    response = TestClient(web_app.app).post(
        "/api/query", json={"question": "What is a habit?"}
    )

    assert response.status_code == 200
    event = json.loads(response.text.removeprefix("data: ").strip())
    assert event == {"type": "error", "message": "Query failed. Please try again."}
    assert "private token" not in response.text

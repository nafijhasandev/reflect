"""
FastAPI web application for the RAG system.

Serves a minimal chat interface and exposes a streaming query API.
The frontend communicates via Server-Sent Events (SSE) for real-time
token-by-token response streaming.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, StringConstraints

import config
from core.bm25_index import BM25Index
from core.book_router import choose_book
from core.embeddings import EmbeddingEngine
from core.general_answer import answer_general_stream
from core.llm_client import LLMClient
from core.query_engine import QueryEngine
from core.query_expander import QueryExpander
from core.reranker import Reranker
from core.retriever import HybridRetriever
from core.scope_checker import is_in_scope
from core.social_reply import social_reply
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Global references set during startup
_engine: QueryEngine | None = None
_engines: dict[str, QueryEngine] = {}
_llm_client: LLMClient | None = None
_reranker: Reranker | None = None
_embedding_engine: EmbeddingEngine | None = None


def _ensure_engine(book: str) -> QueryEngine | None:
    """Load an index created after server startup when it is first requested."""
    global _engine
    if book in _engines:
        return _engines[book]
    if (book not in config.BOOKS or _embedding_engine is None
            or _reranker is None or _llm_client is None):
        return None
    if not config.book_bm25_path(book).is_file():
        return None
    vector_store = VectorStore(book)
    if not vector_store.collection_exists():
        return None
    vector_store.require_cosine()
    try:
        bm25_index = BM25Index.load(config.book_bm25_path(book))
    except FileNotFoundError:
        logger.info("BM25 index for %s is not ready yet.", book)
        return None
    retriever = HybridRetriever(vector_store, bm25_index, _embedding_engine)
    query_expander = QueryExpander(_llm_client, book)
    engine = QueryEngine(retriever, _reranker, _llm_client, query_expander, book)
    _engines[book] = engine
    if book == "atomic_habits":
        _engine = engine
    logger.info("Book index loaded: %s", book)
    return engine


def _refresh_engines() -> None:
    for book in config.BOOKS:
        _ensure_engine(book)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize all RAG components on startup, clean up on shutdown.

    Using the lifespan context manager (FastAPI's recommended pattern)
    rather than on_event decorators which are deprecated.
    """
    global _engine, _embedding_engine, _llm_client, _reranker

    logger.info("Loading RAG components...")

    _embedding_engine = EmbeddingEngine()
    _reranker = Reranker()
    _llm_client = LLMClient()
    _engines.clear()
    _refresh_engines()
    if not _engines:
        raise RuntimeError("No ingested data. Run 'python main.py ingest' first.")
    _engine = _engines.get("atomic_habits")
    logger.info("All RAG components loaded successfully.")

    yield

    # Cleanup
    if _llm_client is not None:
        await _llm_client.close()
    logger.info("RAG system shut down.")


app = FastAPI(title="reflect.", lifespan=lifespan)

# Serve static files (CSS, JS)
app.mount(
    "/static",
    StaticFiles(directory=str(config.PROJECT_ROOT / "web" / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(config.PROJECT_ROOT / "web" / "templates"))


class QueryRequest(BaseModel):
    """Request body for the query endpoint."""
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    book: str = Field(default="atomic_habits", pattern="^(auto|atomic_habits|tiny_habits|power_of_habit|power_of_now|little_book_of_stoicism|five_second_rule|emotional_intelligence|art_of_thinking_clearly|positive_thinking|subconscious_mind)$")
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=config.RERANK_CANDIDATES,
        strict=True,
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serve the chat interface."""
    static_dir = config.PROJECT_ROOT / "web" / "static"
    asset_names = ("style.css", "history.js", "settings.js", "answer_format.js",
                   "stream_events.js", "server_status.js", "app.js")
    asset_version = max((static_dir / name).stat().st_mtime_ns for name in asset_names)
    return templates.TemplateResponse(
        request, "index.html", {"asset_version": asset_version},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/book.pdf")
async def book_pdf(book: str = "atomic_habits") -> FileResponse:
    """Serve the configured book so citations can open its PDF pages."""
    from fastapi import HTTPException
    if book not in config.BOOKS:
        raise HTTPException(status_code=404, detail="Unknown book")
    path = config.book_pdf_path(book)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, media_type="application/pdf")


@app.get("/book-page.png")
def book_page_image(book: str = "atomic_habits", page: int = 1,
                    chunk_id: str = "") -> Response:
    """Render a cited PDF page with its supporting passage highlighted."""
    import pymupdf
    from fastapi import HTTPException

    if book not in config.BOOKS:
        raise HTTPException(status_code=404, detail="Unknown book")
    path = config.book_pdf_path(book)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    with pymupdf.open(path) as document:
        if page < 1 or page > len(document):
            raise HTTPException(status_code=404, detail="Page not found")
        pdf_page = document[page - 1]
        marked = 0
        if chunk_id:
            from core.pdf_highlight import highlight_source, source_chunk

            chunk = source_chunk(book, page, chunk_id)
            if chunk is not None:
                marked = highlight_source(pdf_page, chunk)
        image = pdf_page.get_pixmap(matrix=pymupdf.Matrix(1.7, 1.7), alpha=False)
        return Response(image.tobytes("png"), media_type="image/png",
                        headers={"X-Highlighted-Words": str(marked)})


@app.get("/source-page.pdf")
def highlighted_source_pdf(book: str, chunk_id: str) -> Response:
    """Open real PDF source pages with the strongest answer page first."""
    import pymupdf
    from fastapi import HTTPException

    from core.pdf_highlight import highlight_source, source_chunk

    if book not in config.BOOKS:
        raise HTTPException(status_code=404, detail="Unknown book")
    chunk = source_chunk(book, None, chunk_id)
    path = config.book_pdf_path(book)
    if chunk is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Source not found")

    with pymupdf.open(path) as original:
        first = int(chunk["page_start"])
        last = int(chunk["page_end"])
        if first < 1 or first > len(original) or last < first or last >= first + 5 or last > len(original):
            raise HTTPException(status_code=404, detail="Source page unavailable")
        scores = {page: highlight_source(original[page - 1], chunk)
                  for page in range(first, last + 1)}
        best_page = max(scores, key=scores.get)
        with pymupdf.open() as marked_pdf:
            ordered_pages = [best_page, *(page for page in range(first, last + 1)
                                         if page != best_page)]
            for source_page in ordered_pages:
                marked_pdf.insert_pdf(original, from_page=source_page - 1,
                                      to_page=source_page - 1, annots=True)
            marked_pdf.set_metadata({"title": f"{config.BOOKS[book]['title']} - highlighted source pages"})
            return Response(
                marked_pdf.tobytes(garbage=4, deflate=True), media_type="application/pdf",
                headers={"Content-Disposition": 'inline; filename="highlighted-source.pdf"',
                         "X-Original-PDF-Page": str(best_page),
                         "X-Original-PDF-Pages": ",".join(map(str, ordered_pages)),
                         "Cache-Control": "no-store"},
            )


@app.get("/api/health")
async def health(book: str = "atomic_habits") -> dict[str, Any]:
    """Health check endpoint."""
    llm_configured = False
    if _llm_client is not None:
        llm_configured = await _llm_client.is_available()

    chunk_count = 0
    try:
        if book == "auto":
            _refresh_engines()
            chunk_count = sum(VectorStore(name).count() for name in _engines)
        elif book in config.BOOKS:
            _ensure_engine(book)
            vs = VectorStore() if book == "atomic_habits" else VectorStore(book)
            chunk_count = vs.count()
    except Exception:
        logger.exception("Could not read ChromaDB chunk count")

    return {
        "status": "ok",
        "llm_configured": llm_configured,
        "index_loaded": (bool(_engines) if book == "auto" else
                         _engine is not None if book == "atomic_habits" else book in _engines),
        "chunk_count": chunk_count,
        "supported_books": list(config.BOOKS),
    }


@app.post("/api/query")
async def query_endpoint(req: QueryRequest) -> StreamingResponse:
    """Stream a RAG response as Server-Sent Events.

    SSE format:
        data: {"type": "metadata", "query_type": "..."}
        data: {"type": "chunk", "content": "..."}
        data: {"type": "sources", "sources": [...]}
        data: {"type": "done", "answer": "...", "timing": {...}}
        data: {"type": "error", "message": "..."}
    """
    engine = _engine if req.book == "atomic_habits" else _ensure_engine(req.book)
    if req.book != "auto" and engine is None:
        async def error_stream() -> AsyncGenerator[str, None]:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Book is not indexed. Run python main.py ingest --book ' + req.book})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            started = time.monotonic()
            if req.book == "auto":
                greeting = social_reply(req.question)
                if greeting is not None:
                    for event in (
                        {"type": "metadata", "query_type": "social"},
                        {"type": "chunk", "content": greeting},
                        {"type": "sources", "sources": []},
                        {"type": "done", "answer": greeting,
                         "timing": {"total": time.monotonic() - started}},
                    ):
                        yield f"data: {json.dumps(event)}\n\n"
                    return
            selected_engine = engine
            if req.book == "auto":
                if not any(is_in_scope(req.question, name) for name in config.BOOKS):
                    async for event in answer_general_stream(req.question, _llm_client):
                        yield f"data: {json.dumps(event)}\n\n"
                    return
                _refresh_engines()
                chosen_book = choose_book(req.question, _engines, _reranker)
                if chosen_book is None:
                    async for event in answer_general_stream(req.question, _llm_client):
                        yield f"data: {json.dumps(event)}\n\n"
                    return
                selected_engine = _engines[chosen_book]
                yield f"data: {json.dumps({'type': 'book_selected', 'book': chosen_book})}\n\n"
            async for event in selected_engine.query_stream(req.question, top_k=req.top_k):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:
            logger.exception("Query streaming failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Query failed. Please try again.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

"""
Ingestion pipeline orchestrator.

This module ties together all the steps needed to go from a raw PDF file to a
fully indexed, searchable knowledge base. It is the single entry point for
ingestion and coordinates five sequential stages:

    1. PDF extraction   - read text from the PDF (pdf_processor)
    2. Chunking         - split text into overlapping chunks (chunker)
    3. Embedding        - generate dense vector embeddings (core.embeddings)
    4. Vector storage   - store embeddings in ChromaDB (core.vector_store)
    5. BM25 indexing    - build a sparse keyword index (core.bm25_index)

Why this exists:
    Each stage is implemented in its own module for testability and reuse, but
    a user should not need to call them individually. This orchestrator handles
    ordering, timing, logging, and the "skip if already done" logic so that
    running ingestion is a single function call.

How it works internally:
    run_ingestion() calls each stage in sequence, logs wall-clock time for each
    step, and saves intermediate results (chunks as JSON) for debugging. If the
    ChromaDB collection already contains data, ingestion is skipped unless the
    force flag is set.
"""

import json
import logging
import time
from dataclasses import asdict

import config
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages

logger = logging.getLogger(__name__)


def run_ingestion(force: bool = False, book: str = "atomic_habits") -> None:
    """Run the full ingestion pipeline from PDF to indexed knowledge base.

    This is the main entry point for populating the RAG system's data stores.
    It extracts text from the configured PDF, chunks it, generates embeddings,
    stores them in ChromaDB, and builds a BM25 index.

    The function is idempotent by default: if the ChromaDB collection already
    has data, it skips all work and logs a message. Pass force=True to wipe
    the existing data and re-ingest from scratch.

    Args:
        force: If True, delete existing data and re-ingest even if the
               collection already has data. Defaults to False.

    Raises:
        FileNotFoundError: If the PDF file is missing.
        RuntimeError: If any pipeline stage fails.
    """
    if book not in config.BOOKS:
        raise ValueError(f"Unknown book: {book}")
    pipeline_start = time.time()
    logger.info("=" * 60)
    logger.info("Starting ingestion pipeline")
    logger.info("=" * 60)

    # Lazy imports of core modules so this file can be imported even if
    # core modules are not yet implemented (graceful degradation during dev).
    from core.bm25_index import BM25Index
    from core.embeddings import EmbeddingEngine
    from core.vector_store import VectorStore

    # --- Check if already ingested -------------------------------------------
    vector_store = VectorStore() if book == "atomic_habits" else VectorStore(book=book)

    if not force and vector_store.count() > 0:
        vector_store.require_cosine()
        logger.info(
            "ChromaDB collection '%s' already has %d documents. "
            "Skipping ingestion. Use force=True to re-ingest.",
            book,
            vector_store.count(),
        )
        return

    # --- Step 1: Extract text from PDF ---------------------------------------
    step_start = time.time()
    logger.info("Step 1/5: Extracting text from PDF...")

    pages = extract_pages() if book == "atomic_habits" else extract_pages(config.book_pdf_path(book))
    if book == "power_of_habit":
        from ingestion.power_of_habit import prepare_power_of_habit

        pages = prepare_power_of_habit(pages)
    elif book == "power_of_now":
        from ingestion.power_of_now import prepare_power_of_now

        pages = prepare_power_of_now(pages)
    elif book == "little_book_of_stoicism":
        from ingestion.stoicism import prepare_stoicism

        pages = prepare_stoicism(pages)
    elif book == "five_second_rule":
        from ingestion.five_second_rule import prepare_five_second_rule

        pages = prepare_five_second_rule(pages)
    elif book == "emotional_intelligence":
        from ingestion.emotional_intelligence import prepare_emotional_intelligence

        pages = prepare_emotional_intelligence(pages)
    elif book == "art_of_thinking_clearly":
        from ingestion.art_of_thinking_clearly import prepare_art_of_thinking_clearly

        pages = prepare_art_of_thinking_clearly(pages)
    elif book == "positive_thinking":
        from ingestion.positive_thinking import prepare_positive_thinking

        pages = prepare_positive_thinking(pages)
    elif book == "subconscious_mind":
        from ingestion.subconscious_mind import prepare_subconscious_mind

        pages = prepare_subconscious_mind(pages)

    logger.info(
        "Step 1 complete: %d pages extracted (%.1fs)",
        len(pages), time.time() - step_start,
    )

    # --- Step 2: Chunk the text ----------------------------------------------
    step_start = time.time()
    logger.info("Step 2/5: Chunking text...")

    chunks = chunk_pages(pages) if book == "atomic_habits" else chunk_pages(pages, book=book)
    if not chunks:
        raise ValueError("No text chunks were produced from the PDF.")

    logger.info(
        "Step 2 complete: %d chunks created (%.1fs)",
        len(chunks), time.time() - step_start,
    )

    # --- Step 3: Generate embeddings -----------------------------------------
    step_start = time.time()
    logger.info("Step 3/5: Generating embeddings...")

    embedding_engine = EmbeddingEngine()
    texts = [chunk.text for chunk in chunks]
    embeddings = embedding_engine.embed_texts(texts)

    logger.info(
        "Step 3 complete: %d embeddings generated (%.1fs)",
        len(embeddings), time.time() - step_start,
    )

    # --- Step 4: Store in ChromaDB -------------------------------------------
    step_start = time.time()
    logger.info("Step 4/5: Storing in ChromaDB...")

    if force:
        logger.info("Force flag set - clearing existing data")
        vector_store.reset()

    vector_store.add_chunks(chunks, embeddings)

    logger.info(
        "Step 4 complete: %d documents stored (%.1fs)",
        vector_store.count(), time.time() - step_start,
    )

    # --- Step 5: Build BM25 index --------------------------------------------
    step_start = time.time()
    logger.info("Step 5/5: Building BM25 index...")

    bm25_index = BM25Index()
    bm25_index.build(chunks)
    bm25_index.save(config.book_bm25_path(book))

    logger.info(
        "Step 5 complete: BM25 index built and saved (%.1fs)",
        time.time() - step_start,
    )

    # --- Save chunks JSON for debugging --------------------------------------
    if book == "atomic_habits":
        _save_chunks_json(chunks)
    else:
        _save_chunks_json(chunks, book=book)

    total_time = time.time() - pipeline_start
    logger.info("=" * 60)
    logger.info("Ingestion pipeline complete in %.1fs", total_time)
    logger.info(
        "  Pages: %d | Chunks: %d | Collection: %s",
        len(pages), len(chunks), book,
    )
    logger.info("=" * 60)


def _save_chunks_json(chunks: list, book: str = "atomic_habits") -> None:
    """Save chunks to a JSON file for debugging and inspection.

    The JSON file contains all chunk data (text, metadata, IDs) and is written
    to config.CHUNKS_JSON_PATH. This is purely for human inspection during
    development and is not used by the retrieval pipeline.

    Args:
        chunks: List of Chunk dataclass instances.
    """
    output_path = config.book_chunks_path(book)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(chunk) for chunk in chunks]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Chunks saved to %s (%d chunks)", output_path, len(data))

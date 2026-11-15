"""Extraction, metadata, and citations for the supplied Goleman PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.emotional_intelligence import prepare_emotional_intelligence
from ingestion.pdf_processor import extract_pages


def test_emotional_intelligence_preserves_chapters_appendices_and_pdf_pages():
    pages = prepare_emotional_intelligence(extract_pages(config.EMOTIONAL_INTELLIGENCE_PDF_PATH))
    chapters = {page.chapter for page in pages if page.chapter.startswith("Chapter ")}
    appendices = {page.chapter for page in pages if page.chapter.startswith("Appendix ")}
    assert len(chapters) == 16
    assert len(appendices) == 6
    assert pages[0].page_num == 7
    assert pages[-1].page_num == 282
    assert not any(page.page_num in (12, 36, 122, 174, 211, 283) for page in pages)
    assert next(page for page in pages if page.page_num == 22).chapter == (
        "Chapter 2: Anatomy of an Emotional Hijacking")
    assert next(page for page in pages if page.page_num == 264).chapter == (
        "Appendix A: What Is Emotion?")

    chunks = chunk_pages(pages, book="emotional_intelligence")
    assert any(chunk.page_start <= 25 <= chunk.page_end and chunk.chapter.startswith("Chapter 2:")
               for chunk in chunks)
    assert any(chunk.page_start <= 278 <= chunk.page_end and chunk.chapter.startswith("Appendix F:")
               for chunk in chunks)
    assert all(7 <= chunk.page_start <= chunk.page_end <= 282 for chunk in chunks)
    assert max(chunk.page_end - chunk.page_start + 1 for chunk in chunks) <= 4


def test_emotional_intelligence_prompt_scope_and_citations():
    assert is_in_scope("What is an emotional hijacking?", "emotional_intelligence")
    assert is_in_scope("How can schools teach emotional literacy?", "emotional_intelligence")
    prompt = get_prompt_template("factual", "emotional_intelligence")
    assert "'Emotional Intelligence' by Daniel Goleman" in prompt
    assert "Chapters 1 through 16" in prompt
    chapter_source = {"book": "emotional_intelligence", "metadata": {
        "chapter": "Chapter 2: Anatomy of an Emotional Hijacking",
        "page_start": 25, "page_end": 25,
    }}
    appendix_source = {"book": "emotional_intelligence", "metadata": {
        "chapter": "Appendix A: What Is Emotion?", "page_start": 264, "page_end": 264,
    }}
    assert format_cited_answer("The amygdala can react first.", [chapter_source]) == (
        "The amygdala can react first (Chapter 2, p.25).")
    assert format_cited_answer("The appendix defines emotion.", [appendix_source]) == (
        "The appendix defines emotion (p.264).")

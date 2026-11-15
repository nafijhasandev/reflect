"""Extraction and citations for the supplied Peale PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages
from ingestion.positive_thinking import prepare_positive_thinking


def test_positive_thinking_preserves_split_chapters_and_pdf_pages():
    pages = prepare_positive_thinking(extract_pages(config.POSITIVE_THINKING_PDF_PATH))
    chapters = {page.chapter for page in pages if page.chapter.startswith("Chapter ")}
    assert len(chapters) == 17
    assert pages[0].page_num == 1
    assert pages[-1].page_num == 128
    assert any(page.page_num == 2 and page.chapter.startswith("Introduction:") for page in pages)
    assert any(page.page_num == 2 and page.chapter == "Chapter 1: Believe in Yourself" for page in pages)
    assert any(page.page_num == 67 and page.chapter == "Chapter 9: How to Break the Worry Habit"
               for page in pages)
    assert any(page.page_num == 122 and page.chapter == "Chapter 17: How to Draw Upon Higher Power"
               for page in pages)
    assert all("Power Of Positive Thinking by Noman V Peale" not in page.text for page in pages)
    assert all(not page.text.endswith(f"Page {page.page_num}") for page in pages)

    chunks = chunk_pages(pages, book="positive_thinking")
    assert any(chunk.page_start <= 67 <= chunk.page_end and chunk.chapter.startswith("Chapter 9:")
               for chunk in chunks)
    assert all(1 <= chunk.page_start <= chunk.page_end <= 128 for chunk in chunks)
    assert max(chunk.page_end - chunk.page_start + 1 for chunk in chunks) <= 4


def test_positive_thinking_prompt_scope_and_citations():
    assert is_in_scope("How can I break the worry habit?", "positive_thinking")
    assert is_in_scope("What is prayer power?", "positive_thinking")
    assert is_in_scope("How can I build confidence in myself?", "positive_thinking")
    assert is_in_scope("How can I develop a peaceful mind?", "positive_thinking")
    prompt = get_prompt_template("factual", "positive_thinking")
    assert "'The Power of Positive Thinking' by Norman Vincent Peale" in prompt
    assert "Chapters 1 through 17" in prompt
    chapter_source = {"book": "positive_thinking", "metadata": {
        "chapter": "Chapter 9: How to Break the Worry Habit",
        "page_start": 67, "page_end": 67,
    }}
    intro_source = {"book": "positive_thinking", "metadata": {
        "chapter": "Introduction: What This Book Can Do for You",
        "page_start": 1, "page_end": 1,
    }}
    assert format_cited_answer("Replace worry with faith.", [chapter_source]) == (
        "Replace worry with faith (Chapter 9, p.67).")
    assert format_cited_answer("The opening explains the approach.", [intro_source]) == (
        "The opening explains the approach (p.1).")

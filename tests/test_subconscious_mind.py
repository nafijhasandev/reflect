"""Extraction and citations for the supplied Joseph Murphy PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages
from ingestion.subconscious_mind import prepare_subconscious_mind


def test_subconscious_mind_preserves_20_chapters_and_pdf_pages():
    pages = prepare_subconscious_mind(extract_pages(config.SUBCONSCIOUS_MIND_PDF_PATH))
    chapters = {page.chapter for page in pages if page.chapter.startswith("Chapter ")}
    assert len(chapters) == 20
    assert pages[0].page_num == 5
    assert pages[-1].page_num == 171
    assert not any(page.page_num in (1, 2, 3, 4) for page in pages)
    assert next(page for page in pages if page.page_num == 14).section == (
        "There Is One Mind Common To All Individual Men (Emerson)")
    assert next(page for page in pages if page.page_num == 15).chapter == (
        "Chapter 1: The Treasure House Within You")
    assert next(page for page in pages if page.page_num == 129).chapter.startswith("Chapter 16:")
    assert next(page for page in pages if page.page_num == 161).chapter.startswith("Chapter 20:")
    assert all("More Free Books Law of Attraction Haven" not in page.text for page in pages)
    assert all("I hope you have enjoyed reading" not in page.text for page in pages)

    chunks = chunk_pages(pages, book="subconscious_mind")
    assert any(chunk.page_start <= 24 <= chunk.page_end and chunk.chapter.startswith("Chapter 2:")
               for chunk in chunks)
    assert all(5 <= chunk.page_start <= chunk.page_end <= 171 for chunk in chunks)
    assert max(chunk.page_end - chunk.page_start + 1 for chunk in chunks) <= 4


def test_subconscious_mind_prompt_scope_and_citations():
    assert is_in_scope("How do the conscious and subconscious mind differ?", "subconscious_mind")
    assert is_in_scope("How does suggestion affect the subconscious mind?", "subconscious_mind")
    assert is_in_scope("What does Murphy say about visualization?", "subconscious_mind")
    prompt = get_prompt_template("factual", "subconscious_mind")
    assert "'The Power of Your Subconscious Mind' by Joseph Murphy" in prompt
    assert "Chapters 1 through 20" in prompt
    chapter_source = {"book": "subconscious_mind", "metadata": {
        "chapter": "Chapter 2: How Your Own Mind Works", "page_start": 24, "page_end": 24,
    }}
    opening_source = {"book": "subconscious_mind", "metadata": {
        "chapter": "Introduction", "page_start": 5, "page_end": 5,
    }}
    assert format_cited_answer("The book discusses two levels of mind.", [chapter_source]) == (
        "The book discusses two levels of mind (Chapter 2, p.24).")
    assert format_cited_answer("The opening introduces the approach.", [opening_source]) == (
        "The opening introduces the approach (p.5).")

"""Extraction and citations for the supplied Little Book of Stoicism PDF."""

import re

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages
from ingestion.stoicism import prepare_stoicism


def test_stoicism_preserves_chapters_practices_and_pdf_pages():
    pages = prepare_stoicism(extract_pages(config.STOICISM_PDF_PATH))
    assert min(page.page_num for page in pages) == 5
    assert max(page.page_num for page in pages) == 225
    assert not any(page.page_num in (12, 84) for page in pages)
    assert any(page.page_num == 13 and page.chapter.startswith("Chapter 1:") for page in pages)
    assert any(page.page_num == 186 and page.chapter.startswith("Chapter 8:") for page in pages)
    practices = {
        int(match.group(1)) for page in pages
        if (match := re.match(r"Practice (\d+):", page.section or ""))
    }
    assert practices == set(range(1, 56))

    chunks = chunk_pages(pages, book="little_book_of_stoicism")
    assert any(chunk.page_start == 93 and chunk.section.startswith("Practice 1:")
               for chunk in chunks)
    assert any(chunk.page_start == 224 and chunk.section == "Practice 55: Lead by Example"
               for chunk in chunks)
    assert all(5 <= chunk.page_start <= chunk.page_end <= 225 for chunk in chunks)


def test_stoicism_prompt_scope_and_citations():
    assert is_in_scope("How does negative visualization work?", "little_book_of_stoicism")
    assert is_in_scope("How should I respond to insults?", "little_book_of_stoicism")
    assert is_in_scope("What can I control?", "little_book_of_stoicism")
    prompt = get_prompt_template("factual", "little_book_of_stoicism")
    assert "'The Little Book of Stoicism' by Jonas Salzgeber" in prompt
    assert "55 numbered practices" in prompt
    practice_source = {"book": "little_book_of_stoicism", "metadata": {
        "chapter": "Chapter 6: Preparing Practices", "section": "Practice 9: Morning Routine",
        "page_start": 112, "page_end": 112,
    }}
    intro_source = {"book": "little_book_of_stoicism", "metadata": {
        "chapter": "Introduction", "page_start": 5, "page_end": 5,
    }}
    assert format_cited_answer("Prepare for the day.", [practice_source]) == (
        "Prepare for the day (Chapter 6, p.112).")
    assert format_cited_answer("Stoicism is practical.", [intro_source]) == (
        "Stoicism is practical (p.5).")

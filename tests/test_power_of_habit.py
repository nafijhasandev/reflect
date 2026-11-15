"""Full-book extraction and section boundaries for The Power of Habit."""

import pymupdf

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages
from ingestion.power_of_habit import prepare_power_of_habit


def test_full_book_preparation_keeps_chapters_and_sections():
    with pymupdf.open(config.POWER_OF_HABIT_PDF_PATH) as document:
        assert len(document) == 386

    pages = prepare_power_of_habit(extract_pages(config.POWER_OF_HABIT_PDF_PATH))
    assert len({page.page_num for page in pages}) == 289
    assert (pages[0].page_num, pages[-1].page_num) == (11, 306)
    assert len({page.chapter for page in pages}) == 11  # Prologue, nine chapters, appendix.
    assert len({page.section for page in pages}) == 39
    assert any(page.chapter.startswith("Chapter 9:") for page in pages)
    assert any(page.chapter.startswith("Appendix:") for page in pages)
    assert all("Duhi_" not in page.text and "10/17/11" not in page.text for page in pages)

    chunks = chunk_pages(pages, book="power_of_habit")
    assert len(chunks) > 800
    assert {chunk.section for chunk in chunks} == {page.section for page in pages}
    assert all(11 <= chunk.page_start <= chunk.page_end <= 306 for chunk in chunks)


def test_power_of_habit_prompt_and_citations_cover_full_book():
    prompt = get_prompt_template("factual", "power_of_habit")
    assert "'The Power of Habit' by Charles Duhigg" in prompt
    assert "Chapters 1 through 9" in prompt
    assert "Chapter One only" not in prompt

    chapter_source = {"book": "power_of_habit", "metadata": {
        "chapter": "Chapter 9: The Neurology of Free Will", "page_start": 265, "page_end": 266,
    }}
    appendix_source = {"book": "power_of_habit", "metadata": {
        "chapter": "Appendix: A Reader's Guide to Using These Ideas", "page_start": 295, "page_end": 296,
    }}
    assert format_cited_answer("The loop matters (Chapter 9, p.265).", [chapter_source]) == (
        "The loop matters (Chapter 9, p.265)."
    )
    assert format_cited_answer("Diagnose the cue (p.295).", [appendix_source]) == (
        "Diagnose the cue (p.295)."
    )

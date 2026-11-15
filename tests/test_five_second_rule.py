"""Extraction and citations for the supplied full 5 Second Rule PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.five_second_rule import prepare_five_second_rule
from ingestion.pdf_processor import extract_pages


def test_five_second_rule_preserves_chapters_sections_and_pdf_pages():
    pages = prepare_five_second_rule(extract_pages(config.FIVE_SECOND_RULE_PDF_PATH))
    chapters = {page.chapter for page in pages if page.chapter.startswith("Chapter ")}
    assert len(chapters) == 17
    assert min(page.page_num for page in pages) == 6
    assert max(page.page_num for page in pages) == 251
    assert not any(page.page_num in (7, 65, 120, 166, 198, 240, 252) for page in pages)
    assert any(page.page_num == 8 and page.text.startswith(
        "Chapter 1: Five Seconds to Change Your Life\n\nYou are") for page in pages)
    assert any(page.page_num == 202 and "A big mistake" in page.text for page in pages)
    assert any(page.page_num == 121 and "I like to say" in page.text for page in pages)
    assert any(page.page_num == 228 and page.chapter.startswith("Chapter 17:")
               for page in pages)

    chunks = chunk_pages(pages, book="five_second_rule")
    assert any(chunk.page_start <= 110 <= chunk.page_end and
               chunk.chapter.startswith("Chapter 8:") for chunk in chunks)
    assert any(chunk.page_start <= 241 <= chunk.page_end and
               chunk.chapter == "The Power of You" for chunk in chunks)
    assert all(6 <= chunk.page_start <= chunk.page_end <= 251 for chunk in chunks)


def test_five_second_rule_prompt_scope_and_citations():
    assert is_in_scope("Why does counting backward help?", "five_second_rule")
    assert is_in_scope("What is the Wake Up Challenge?", "five_second_rule")
    prompt = get_prompt_template("factual", "five_second_rule")
    assert "'The 5 Second Rule' by Mel Robbins" in prompt
    assert "Chapters 1 through 17" in prompt
    chapter_source = {"book": "five_second_rule", "metadata": {
        "chapter": "Chapter 8: How to Start Using the Rule",
        "page_start": 110, "page_end": 110,
    }}
    closing_source = {"book": "five_second_rule", "metadata": {
        "chapter": "The Power of You", "page_start": 241, "page_end": 241,
    }}
    assert format_cited_answer("Start with the alarm.", [chapter_source]) == (
        "Start with the alarm (Chapter 8, p.110).")
    assert format_cited_answer("Move toward your goal.", [closing_source]) == (
        "Move toward your goal (p.241).")

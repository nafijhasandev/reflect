"""Extraction and citations for the supplied Power of Now PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages
from ingestion.power_of_now import prepare_power_of_now


def test_power_of_now_keeps_correct_chapter_and_pdf_pages():
    pages = prepare_power_of_now(extract_pages(config.POWER_OF_NOW_PDF_PATH))
    assert pages[0].page_num == 19
    assert max(page.page_num for page in pages) == 220
    for page_num, chapter in ((26, 1), (58, 3), (80, 4), (198, 10)):
        assert any(page.page_num == page_num and
                   page.chapter.startswith(f"Chapter {chapter}:") for page in pages)
    assert not any("YOU YOU YOU" in page.text for page in pages)

    chunks = chunk_pages(pages, book="power_of_now")
    assert any(chunk.page_start <= 198 <= chunk.page_end and
               chunk.chapter.startswith("Chapter 10:") for chunk in chunks)
    assert all(chunk.page_start >= 19 for chunk in chunks)
    assert not any(len(chunk.text) < 110 and chunk.text.isupper() for chunk in chunks)


def test_power_of_now_prompt_and_citations():
    assert is_in_scope("What does the Now mean?", "power_of_now")
    assert is_in_scope("How does Tolle describe consciousness?", "power_of_now")
    prompt = get_prompt_template("factual", "power_of_now")
    assert "'The Power of Now' by Eckhart Tolle" in prompt
    assert "Chapters 1 through 10" in prompt
    chapter_source = {"book": "power_of_now", "metadata": {
        "chapter": "Chapter 10: The Meaning of Surrender",
        "page_start": 198, "page_end": 198,
    }}
    intro_source = {"book": "power_of_now", "metadata": {
        "chapter": "Introduction", "page_start": 19, "page_end": 19,
    }}
    assert format_cited_answer("Accept the Now.", [chapter_source]) == "Accept the Now (Chapter 10, p.198)."
    assert format_cited_answer("Observe thought.", [intro_source]) == "Observe thought (p.19)."

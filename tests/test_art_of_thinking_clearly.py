"""Extraction and citations for the supplied 2013 Dobelli PDF."""

import config
from core.citations import format_cited_answer
from core.query_classifier import get_prompt_template
from core.scope_checker import is_in_scope
from ingestion.art_of_thinking_clearly import prepare_art_of_thinking_clearly
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import extract_pages


def test_dobelli_preserves_99_bias_chapters_and_pdf_pages():
    pages = prepare_art_of_thinking_clearly(extract_pages(config.ART_OF_THINKING_CLEARLY_PDF_PATH))
    chapters = {page.chapter for page in pages if page.chapter.startswith("Chapter ")}
    assert len(chapters) == 99
    assert pages[0].page_num == 10
    assert pages[-1].page_num == 222
    assert not any(page.page_num in (5, 9, 223, 224, 225) for page in pages)
    assert next(page for page in pages if page.page_num == 13).chapter == "Chapter 1: Survivorship Bias"
    assert next(page for page in pages if page.page_num == 22).chapter == "Chapter 5: Sunk Cost Fallacy"
    assert next(page for page in pages if page.page_num == 215).chapter == "Chapter 99: News Illusion"
    assert next(page for page in pages if page.page_num == 217).chapter == "Epilogue"

    chunks = chunk_pages(pages, book="art_of_thinking_clearly")
    assert any(chunk.page_start <= 22 <= chunk.page_end and chunk.chapter == "Chapter 5: Sunk Cost Fallacy"
               for chunk in chunks)
    assert all(10 <= chunk.page_start <= chunk.page_end <= 222 for chunk in chunks)
    assert max(chunk.page_end - chunk.page_start + 1 for chunk in chunks) <= 4


def test_dobelli_prompt_scope_and_citations():
    assert is_in_scope("What is survivorship bias?", "art_of_thinking_clearly")
    assert is_in_scope("How does the sunk cost fallacy affect decisions?", "art_of_thinking_clearly")
    assert is_in_scope("What is the Zeigarnik effect?", "art_of_thinking_clearly")
    assert is_in_scope("Why do last chances make us panic?", "art_of_thinking_clearly")
    prompt = get_prompt_template("factual", "art_of_thinking_clearly")
    assert "'The Art of Thinking Clearly' by Rolf Dobelli" in prompt
    assert "Chapters 1 through 99" in prompt
    chapter_source = {"book": "art_of_thinking_clearly", "metadata": {
        "chapter": "Chapter 5: Sunk Cost Fallacy", "page_start": 22, "page_end": 22,
    }}
    epilogue_source = {"book": "art_of_thinking_clearly", "metadata": {
        "chapter": "Epilogue", "page_start": 217, "page_end": 217,
    }}
    assert format_cited_answer("Past costs can distort choices.", [chapter_source]) == (
        "Past costs can distort choices (Chapter 5, p.22).")
    assert format_cited_answer("The closing section returns to clear thinking.", [epilogue_source]) == (
        "The closing section returns to clear thinking (p.217).")
    final_chapter = {"book": "art_of_thinking_clearly", "metadata": {
        "chapter": "Chapter 99: News Illusion", "page_start": 215, "page_end": 215,
    }}
    assert format_cited_answer("News can distort risk perception.", [final_chapter]) == (
        "News can distort risk perception (Chapter 99, p.215).")

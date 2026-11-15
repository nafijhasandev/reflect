"""Bookey-specific chunk boundaries and citation metadata."""

import pytest

import config
from ingestion.chunker import chunk_pages
from ingestion.pdf_processor import Page, extract_pages
from ingestion.tiny_habits import _is_summary_heading


def test_bookey_questions_keep_answers_and_cross_page_citations():
    pages = [
        Page(2, "Written by Bookey", None, None),
        Page(6, "Summary Content List\n\nChapter 1 : THE ELEMENTS OF BEHAVIOR"
             "\n\nChapter 2 : MOTIVATION", None, None),
        Page(7, "Chapter 1 Summary : THE ELEMENTS OF BEHAVIOR\n\n"
             "Focus Map\n\nA focus map helps choose behaviors.", None, None,
             topic_headings=["Focus Map"]),
        Page(58, "Tiny Habits Questions View on Bookey Website\n\n"
             "Chapter 1 | THE ELEMENTS OF BEHAVIOR| Q&A\n\n"
             "1.Question\n\nWhat drives behavior? Answer:Motivation and", None, None),
        Page(59, "ability and a prompt.\n\n2.Question\n\n"
             "Can habits be tiny? Answer:Yes, start small.", None, None),
        Page(60, "Chapter 2 | MOTIVATION| Q&A\n\n1.Question\n\n"
             "Why is motivation unreliable? Answer:It fluctuates.", None, None),
        Page(94, "Tiny Habits Quiz and Test\n\n"
             "1.Motivation is the only thing needed for change.", None, None),
    ]

    chunks = chunk_pages(pages, book="tiny_habits")
    questions = [chunk for chunk in chunks if chunk.text.startswith("Question:")]

    assert len(questions) == 3
    assert questions[0].text == (
        "Question: What drives behavior?\nAnswer: Motivation and ability and a prompt."
    )
    assert (questions[0].page_start, questions[0].page_end) == (58, 59)
    assert questions[0].chapter == "Chapter 1: THE ELEMENTS OF BEHAVIOR"
    assert questions[2].chapter == "Chapter 2: MOTIVATION"
    assert any(chunk.section == "Focus Map" for chunk in chunks)
    assert all(chunk.page_start < 94 for chunk in chunks)
    assert all("Bookey" not in chunk.text for chunk in chunks)


def test_other_tiny_habits_pdfs_use_general_topic_chunking():
    pages = [Page(1, "ANCHOR\n\nAn existing action can prompt a new one.",
                  "Chapter 1", None, topic_headings=["ANCHOR"])]

    chunks = chunk_pages(pages, book="tiny_habits")

    assert len(chunks) == 1
    assert chunks[0].section == "ANCHOR"
    assert "An existing action" in chunks[0].text


def test_bookey_body_fragment_does_not_replace_its_topic():
    pages = [
        Page(2, "Written by Bookey", None, None),
        Page(7, "Chapter 1 Summary : THE ELEMENTS OF BEHAVIOR\n\n"
             "Understanding Change: Small vs. Big Actions\n\n"
             "The misconception that big changes lead to success\n\n"
             "is challenged by small actions.", None, None,
             topic_headings=["Understanding Change: Small vs. Big Actions",
                             "The misconception that big changes lead to success"]),
    ]

    chunks = chunk_pages(pages, book="tiny_habits")

    assert any(chunk.section == "Understanding Change: Small vs. Big Actions"
               and "misconception" in chunk.text for chunk in chunks)
    assert not any(chunk.section == "The misconception that big changes lead to success"
                   for chunk in chunks)


@pytest.mark.skipif(not config.TINY_HABITS_PDF_PATH.exists(), reason="Local book PDF is absent")
def test_supplied_summary_keeps_all_eight_chapters_and_complete_questions():
    pages = extract_pages(config.TINY_HABITS_PDF_PATH)
    chunks = chunk_pages(pages, book="tiny_habits")
    questions = [chunk for chunk in chunks if chunk.text.startswith("Question:")]

    assert len(questions) == 80
    assert all("\nAnswer: " in chunk.text for chunk in questions)
    assert all(chunk.page_start < 94 for chunk in chunks)
    assert all(len(chunk.text) <= config.CHUNK_SIZE for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert len(chunks) >= 280
    summary_headings = {
        heading
        for page in pages if 7 <= page.page_num <= 45
        for heading in page.topic_headings or []
        if _is_summary_heading(heading)
        and heading in page.text
        and not heading.startswith(("Chapter", "Install", "Audio", "Summary of Chapter"))
        and len(heading) <= 90
        and not heading.endswith((".", "?", "!"))
    }
    assert all(any(chunk.section == heading and chunk.text.strip() != heading
                   for chunk in chunks) for heading in summary_headings)
    for section in (
        "Understanding Change: Small vs. Big Actions",
        "Progress and Relationship Improvement",
        "Conclusion: Embracing Change for Collective Good",
    ):
        assert any(chunk.section == section and chunk.text != section for chunk in chunks)
    for chapter in range(1, 9):
        label = f"Chapter {chapter}:"
        assert sum(chunk.chapter.startswith(label) for chunk in questions) == 10

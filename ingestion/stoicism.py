"""Prepare the supplied Little Book of Stoicism PDF for section-aware retrieval."""

import re
from bisect import bisect_right
from dataclasses import replace

from ingestion.pdf_processor import Page


# PDF page numbers for the 229-page edition in this project. The generic
# heading detector misses its separate "Chapter N" and title text blocks.
_CHAPTER_STARTS = (13, 25, 33, 74, 85, 92, 144, 186)
_CHAPTER_TITLES = (
    "The Promise of Stoic Philosophy",
    "A Quick History Lesson",
    "The Stoic Happiness Triangle",
    "The Villain: Negative Emotions Get in the Way",
    "How to Practice Stoicism?",
    "Preparing Practices",
    "Situational Practices: How to Deal with Yourself when Life Gets Tough?",
    "Situational Practices: How to Handle Yourself When Other People Challenge You?",
)
_PRACTICE = re.compile(r"Practice\s+(\d{1,2})$", re.IGNORECASE)


def _practice_heading(paragraphs: list[str]) -> tuple[str, int]:
    """Return a practice label and number of title paragraphs to consume."""
    number = int(_PRACTICE.fullmatch(paragraphs[0]).group(1))
    title = paragraphs[1]
    consumed = 2
    if (len(paragraphs) > 3 and len(paragraphs[2]) < 45
            and paragraphs[2][0] not in "�\"'“(" and
            not paragraphs[2].endswith((".", "?", "!", ":"))):
        title += " " + paragraphs[2]
        consumed += 1
    return f"Practice {number}: {title}", consumed


def prepare_stoicism(pages: list[Page]) -> list[Page]:
    """Keep introduction, eight chapters, and 55 complete practice sections.

    Exclude cover, disclaimer, part title pages, acknowledgments, bibliography,
    and promotion. Chunk metadata uses physical PDF pages for source links.
    """
    prepared: list[Page] = []
    current_section = "Introduction"
    in_practices = False
    seen_practices: list[int] = []

    for page in pages:
        if page.page_num < 5 or page.page_num > 225 or page.page_num in (12, 84):
            continue

        chapter_index = bisect_right(_CHAPTER_STARTS, page.page_num) - 1
        chapter = (f"Chapter {chapter_index + 1}: {_CHAPTER_TITLES[chapter_index]}"
                   if chapter_index >= 0 else "Introduction")
        paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        if not paragraphs:
            continue

        if page.page_num == 5 and paragraphs[0] == "Introduction":
            paragraphs = paragraphs[1:]
        if page.page_num in _CHAPTER_STARTS:
            in_practices = False
            current_section = chapter
            # The long chapter titles on these pages occupy two text blocks.
            title_blocks = 2 if page.page_num in (74, 144, 186) else 1
            paragraphs = [chapter, *paragraphs[1 + title_blocks:]]

        if paragraphs and _PRACTICE.fullmatch(paragraphs[0]):
            practice = int(_PRACTICE.fullmatch(paragraphs[0]).group(1))
            if practice != len(seen_practices) + 1:
                raise ValueError(f"Unexpected practice {practice} on PDF page {page.page_num}")
            seen_practices.append(practice)
            current_section, consumed = _practice_heading(paragraphs)
            paragraphs = [current_section, *paragraphs[consumed:]]
            in_practices = True

        segment: list[str] = []

        def save_segment() -> None:
            if segment:
                text = "\n\n".join(segment)
                prepared.append(replace(page, text=text, chapter=chapter,
                                        section=current_section,
                                        lines=text.splitlines(), topic_headings=None))
                segment.clear()

        headings = set(page.topic_headings or [])
        for paragraph in paragraphs:
            if (not in_practices and paragraph in headings
                    and not paragraph.startswith(("Chapter ", "Practice "))):
                save_segment()
                current_section = paragraph
            segment.append(paragraph)
        save_segment()

    if seen_practices != list(range(1, 56)):
        raise ValueError(f"Expected 55 Stoic practices, found {len(seen_practices)}")
    return prepared

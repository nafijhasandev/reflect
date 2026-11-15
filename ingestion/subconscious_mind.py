"""Prepare the supplied 171-page Joseph Murphy PDF for search."""

import re
from bisect import bisect_right
from dataclasses import replace

import pymupdf

import config
from ingestion.pdf_processor import Page


_CHAPTER_ENTRY = re.compile(r"^Chapter\s+([IVX]+)\s+(.+)$", re.IGNORECASE)
_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
          "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX")
_FOOTER = "More Free Books Law of Attraction Haven"
_PROMOTION = "I hope you have enjoyed reading The Power of Your Subconscious Mind"


def _contents() -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Read opening section and chapter starts from the PDF bookmarks."""
    with pymupdf.open(config.SUBCONSCIOUS_MIND_PDF_PATH) as pdf:
        entries = [(page, title.strip()) for _, title, page in pdf.get_toc()]
    opening = [(page, title) for page, title in entries if page < 15]
    chapters = []
    for page, title in entries:
        match = _CHAPTER_ENTRY.fullmatch(title)
        if match:
            roman, name = match.groups()
            number = _ROMAN.index(roman.upper()) + 1
            chapters.append((page, f"Chapter {number}: {name}"))
    if (len(opening) != 10 or [page for page, _ in opening] != list(range(5, 15))
            or len(chapters) != 20
            or [name.split(":", 1)[0] for _, name in chapters]
            != [f"Chapter {number}" for number in range(1, 21)]
            or any(left[0] >= right[0] for left, right in zip(chapters, chapters[1:]))):
        raise ValueError("Unexpected contents in The Power of Your Subconscious Mind PDF")
    return opening, chapters


def prepare_subconscious_mind(pages: list[Page]) -> list[Page]:
    """Keep ten opening topics and 20 chapters with original PDF page numbers."""
    opening, chapters = _contents()
    chapter_starts = [page for page, _ in chapters]
    opening_by_page = dict(opening)
    prepared: list[Page] = []
    for page in pages:
        number = page.page_num
        if number < 5:
            continue
        if number < chapter_starts[0]:
            chapter = "Introduction"
            section = opening_by_page[number]
        else:
            chapter = chapters[bisect_right(chapter_starts, number) - 1][1]
            section = chapter

        paragraphs = []
        for paragraph in page.text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph or paragraph == _FOOTER:
                continue
            if paragraph.startswith(_PROMOTION):
                break
            paragraphs.append(paragraph)
        if not paragraphs:
            continue
        if number in opening_by_page or number in chapter_starts:
            opening_parts = 3 if number in (14, 129) else 2
            if len(paragraphs) < opening_parts:
                raise ValueError(f"Missing opening text on PDF page {number}")
            # Keep each heading with its first body passage for retrieval.
            paragraphs[:opening_parts] = [" ".join(paragraphs[:opening_parts])]
        text = "\n\n".join(paragraphs)
        headings = [heading for heading in page.topic_headings or []
                    if not heading.startswith("Chapter ") and heading != _FOOTER]
        prepared.append(replace(page, text=text, lines=text.splitlines(),
                                chapter=chapter, section=section,
                                topic_headings=headings if number >= 15 else None))
    return prepared

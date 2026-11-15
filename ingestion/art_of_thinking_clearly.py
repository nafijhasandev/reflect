"""Prepare the supplied 2013 Dobelli PDF for chapter-aware search."""

import re
from bisect import bisect_right
from dataclasses import replace

import pymupdf

import config
from ingestion.pdf_processor import Page


_NUMBERED_ENTRY = re.compile(r"^(\d+)\s+(.+?):\s*(.+)$")


def _chapter_entries() -> list[tuple[int, str, str]]:
    """Read each chapter's physical PDF start page and two-part title."""
    with pymupdf.open(config.ART_OF_THINKING_CLEARLY_PDF_PATH) as pdf:
        entries = []
        for _, title, page in pdf.get_toc():
            match = _NUMBERED_ENTRY.match(title)
            if match:
                number, heading, bias = match.groups()
                entries.append((page, f"Chapter {number}: {bias.strip()}", heading.strip()))
    if len(entries) != 99 or any(
        not chapter.startswith(f"Chapter {number}:")
        for number, (_, chapter, _) in enumerate(entries, start=1)
    ) or any(left[0] >= right[0] for left, right in zip(entries, entries[1:])):
        raise ValueError("Unexpected chapter layout in The Art of Thinking Clearly PDF")
    return entries


def prepare_art_of_thinking_clearly(pages: list[Page]) -> list[Page]:
    """Keep introduction, 99 biases, and epilogue with physical PDF pages.

    The generic chapter detector misses this edition's numbered two-part
    headings and can mistake body text for topic headings. The PDF bookmarks
    provide reliable chapter starts. Contents and publisher matter are excluded.
    """
    entries = _chapter_entries()
    starts = [page for page, _, _ in entries]
    start_pages = set(starts)
    prepared: list[Page] = []
    for page in pages:
        number = page.page_num
        if number < 10 or number >= 223:
            continue
        if number < starts[0]:
            chapter = section = "Introduction"
        elif number >= 217:
            chapter = section = "Epilogue"
        else:
            _, chapter, section = entries[bisect_right(starts, number) - 1]
        text = page.text
        if number in start_pages:
            paragraphs = text.split("\n\n")
            if len(paragraphs) < 3:
                raise ValueError(f"Missing chapter opening on PDF page {number}")
            # Keep the rhetorical heading and bias name with their first body
            # paragraph, avoiding a searchable chunk with only a title.
            text = "\n\n".join([" ".join(paragraphs[:3]), *paragraphs[3:]])
        prepared.append(replace(page, text=text, lines=text.splitlines(),
                                chapter=chapter, section=section,
                                topic_headings=None))
    return prepared

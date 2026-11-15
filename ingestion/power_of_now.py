"""Clean the supplied 220-page Power of Now edition for section-aware search."""

import re
from bisect import bisect_right
from dataclasses import replace

from ingestion.pdf_processor import Page


# These are PDF page numbers in the edition shipped with this project.
_CHAPTER_STARTS = (26, 45, 58, 80, 99, 112, 132, 146, 173, 198)
_CHAPTER_TITLES = (
    "You Are Not Your Mind",
    "Consciousness: The Way Out of Pain",
    "Moving Deeply into the Now",
    "Mind Strategies for Avoiding the Now",
    "The State of Presence",
    "The Inner Body",
    "Portals into the Unmanifested",
    "Enlightened Relationships",
    "Beyond Happiness and Unhappiness",
    "The Meaning of Surrender",
)
_REPEATED_WORD = re.compile(r"(?i)(?<!\S)([A-Za-z][A-Za-z'’:-]*)(?:\s+\1){3}(?!\S)")
_CHAPTER_LINE = re.compile(r"Chapter\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)", re.I)


def _clean(paragraph: str) -> str:
    cleaned = _REPEATED_WORD.sub(r"\1", paragraph).strip()
    return cleaned.replace("AVOIDING VOIDING VOIDING VOIDING", "AVOIDING")


def prepare_power_of_now(pages: list[Page]) -> list[Page]:
    """Keep the introduction and ten chapters with correct PDF page numbers.

    The PDF repeats every word in its large headings. It also prints "Chapter
    One" at the starts of chapters 3 and 4, and omits the number on chapter
    10. Page boundaries provide reliable chapter labels for this edition.
    """
    prepared: list[Page] = []
    current_section = "Introduction"

    for page in pages:
        if page.page_num < 19:
            continue
        index = bisect_right(_CHAPTER_STARTS, page.page_num) - 1
        chapter = (f"Chapter {index + 1}: {_CHAPTER_TITLES[index]}"
                   if index >= 0 else "Introduction")
        if page.page_num in _CHAPTER_STARTS:
            current_section = chapter

        segment: list[str] = []

        def save_segment() -> None:
            if segment:
                text = "\n\n".join(segment)
                if not (len(segment) == 1 and text.isupper() and len(text) <= 110):
                    prepared.append(replace(page, text=text, chapter=chapter,
                                            section=current_section,
                                            lines=text.splitlines(), topic_headings=None))
                segment.clear()

        for raw in page.text.split("\n\n"):
            paragraph = _clean(raw)
            if not paragraph or _CHAPTER_LINE.fullmatch(paragraph):
                continue
            if paragraph == "�� END ��":
                continue
            if paragraph.isupper() and len(paragraph) <= 110 and len(paragraph.split()) >= 2:
                save_segment()
                current_section = paragraph.title().replace("'T", "'t").replace("'S", "'s")
                # A heading without body text is useful as metadata, not as a
                # standalone retrieval passage.
                segment.append(paragraph)
                continue
            segment.append(paragraph)
        save_segment()

    return prepared

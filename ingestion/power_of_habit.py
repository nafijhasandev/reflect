"""Prepare the full Power of Habit PDF for section-aware retrieval."""

import re
from bisect import bisect_right
from dataclasses import replace

from ingestion.pdf_processor import Page


# PDF page numbers for the 386-page edition in this project. These stay as
# PDF page numbers in chunk metadata, so a source link opens the correct page.
_CHAPTER_STARTS = (23, 51, 80, 117, 147, 174, 202, 235, 265)
_CHAPTER_TITLES = (
    "The Habit Loop",
    "The Craving Brain",
    "The Golden Rule of Habit Change",
    "Keystone Habits, or the Ballad of Paul O'Neill",
    "Starbucks and the Habit of Success",
    "The Power of a Crisis",
    "How Target Knows What You Want Before You Do",
    "Saddleback Church and the Montgomery Bus Boycott",
    "The Neurology of Free Will",
)
_PART_TITLE_PAGES = {21, 22, 115, 116, 233, 234}
_ROMAN_MARKER = re.compile(r"[IVX\s]{1,12}\.")
_INDESIGN_FOOTER = re.compile(r"Duhi_\S+?\.indd\s+[ivxlcdm\d]+", re.IGNORECASE)
_TIMESTAMP = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2}\s+\d{1,2}:\d{2}\s+[AP]M\b")
_CHART_LABELS = {"Click", "First Section", "Second Section", "Chocolate"}


def _chapter(page_num: int) -> str | None:
    if page_num < 11 or page_num > 306 or page_num in _PART_TITLE_PAGES:
        return None
    if page_num < 23:
        return "Prologue: The Habit Cure"
    if page_num >= 295:
        return "Appendix: A Reader's Guide to Using These Ideas"
    index = bisect_right(_CHAPTER_STARTS, page_num) - 1
    return f"Chapter {index + 1}: {_CHAPTER_TITLES[index]}"


def _clean_paragraph(paragraph: str) -> str:
    paragraph = _INDESIGN_FOOTER.sub("", paragraph)
    paragraph = _TIMESTAMP.sub("", paragraph)
    paragraph = paragraph.translate(str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "�": "'"}))
    paragraph = re.sub(r"(fi|fl)\s+(?=[a-z])", r"\1", paragraph)
    paragraph = re.sub(r"\b([A-Za-z]+)-\s+([A-Za-z]+)\b", r"\1-\2", paragraph)
    return paragraph.strip()


def _is_print_artifact(paragraph: str) -> bool:
    if not paragraph or paragraph in _CHART_LABELS:
        return True
    if "●" in paragraph and len(paragraph) < 100:
        return True
    if paragraph == "T H E P O W E R O F H A B I T":
        return True
    return False


def prepare_power_of_habit(pages: list[Page]) -> list[Page]:
    """Keep the prologue, nine chapters, and appendix with true section breaks.

    The table of contents, part title pages, acknowledgments, bibliography,
    notes, and index do not provide useful answer passages. Roman numerals in
    the body mark 37 chapter sections; a page can contain two such sections.
    """
    prepared: list[Page] = []
    current_chapter: str | None = None
    current_section: str | None = None

    for page in pages:
        chapter = _chapter(page.page_num)
        if chapter is None:
            continue
        if chapter != current_chapter:
            current_chapter = chapter
            current_section = chapter

        paragraphs = [_clean_paragraph(text) for text in page.text.split("\n\n")]
        paragraphs = [text for text in paragraphs if not _is_print_artifact(text)]

        if page.page_num in _CHAPTER_STARTS:
            first_marker = next(
                (i for i, text in enumerate(paragraphs) if _ROMAN_MARKER.fullmatch(text)),
                None,
            )
            if first_marker is None:
                raise ValueError(f"Chapter heading not found on PDF page {page.page_num}")
            paragraphs = paragraphs[first_marker:]
        elif page.page_num in (11, 295):
            paragraphs = paragraphs[2:]  # Prologue/appendix title and subtitle.

        segment: list[str] = []

        def save_segment() -> None:
            if not segment:
                return
            text = "\n\n".join(segment)
            prepared.append(replace(
                page,
                text=text,
                chapter=current_chapter,
                section=current_section,
                lines=text.splitlines(),
                topic_headings=None,
            ))
            segment.clear()

        for paragraph in paragraphs:
            if _ROMAN_MARKER.fullmatch(paragraph):
                save_segment()
                numeral = paragraph.replace(" ", "").rstrip(".")
                current_section = f"{current_chapter} — Section {numeral}"
            else:
                segment.append(paragraph)
        save_segment()

    return prepared

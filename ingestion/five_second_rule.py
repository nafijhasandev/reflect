"""Prepare the supplied full 5 Second Rule PDF for chapter-aware search."""

from bisect import bisect_right
from dataclasses import replace

from ingestion.pdf_processor import Page


# Physical PDF pages for the 252-page edition in this project. The generic
# chapter detector cannot read its spelled-out chapter numbers and drop caps.
_CHAPTER_STARTS = (8, 29, 40, 54, 66, 80, 96, 110, 124, 139, 152,
                   171, 180, 191, 202, 218, 228)
_CHAPTER_TITLES = (
    "Five Seconds to Change Your Life",
    "How I Discovered the 5 Second Rule",
    "What You Can Expect When You Use It",
    "Why the Rule Works",
    "Everyday Courage",
    "What Are You Waiting For?",
    "You'll Never Feel Like It",
    "How to Start Using the Rule",
    "Improve Your Health",
    "Increase Productivity",
    "End Procrastination",
    "Stop Worrying",
    "End Anxiety",
    "Beat Fear",
    "Building Real Confidence",
    "Pursuing Passion",
    "Enrich Your Relationships",
)
_PART_PAGES = {7, 65, 120, 166, 198, 240}
_INTERLUDES = (
    (121, 124, "Part 3: Courage Changes Your Behavior",
     "How to Become the Most Productive Person You Know", 1),
    (167, 171, "Part 4: Courage Changes Your Mind",
     "How to Become the Happiest Person You Know", 2),
    (199, 202, "Part 5: Courage Changes Everything",
     "How to Become the Most Fulfilled Person You Know", 2),
)


def _rebuild_opening(page: Page, label: str, title_blocks: int,
                     has_chapter_marker: bool) -> tuple[str, list[str]]:
    """Join the large drop cap to its first word and remove title blocks."""
    paragraphs = [part.strip() for part in page.text.split("\n\n") if part.strip()]
    header_end = 1 + title_blocks + int(has_chapter_marker)
    if len(paragraphs) <= header_end or len(paragraphs[0]) != 1:
        raise ValueError(f"Unexpected title layout on PDF page {page.page_num}")
    header = set(paragraphs[1:header_end])
    body = paragraphs[header_end:]
    separator = " " if page.page_num in (121, 202) else ""
    body[0] = paragraphs[0] + separator + body[0]
    return "\n\n".join([label, *body]), [
        heading for heading in page.topic_headings or [] if heading not in header
    ]


def prepare_five_second_rule(pages: list[Page]) -> list[Page]:
    """Keep the opening, 17 chapters, three interludes, and closing section.

    Contents, part title pages, image-only pages, and the final promotional page
    are excluded. Page metadata always refers to the original PDF page.
    """
    prepared: list[Page] = []
    for page in pages:
        number = page.page_num
        if number < 6 or number > 251 or number in _PART_PAGES:
            continue

        if number == 6:
            chapter = "Opening: Everyday Courage"
            section = chapter
            text = page.text
            headings = None
        elif 241 <= number <= 251:
            chapter = "The Power of You"
            section = "The 5 Second Rule" if number == 251 else chapter
            text = page.text
            headings = None
            if number == 241:
                text, _ = _rebuild_opening(page, chapter, 1, False)
        elif interlude := next((item for item in _INTERLUDES
                                if item[0] <= number < item[1]), None):
            start, _, chapter, section, title_blocks = interlude
            headings = None
            text = page.text
            if number == start:
                text, _ = _rebuild_opening(page, section, title_blocks, False)
        else:
            index = bisect_right(_CHAPTER_STARTS, number) - 1
            if index < 0:
                continue
            chapter = f"Chapter {index + 1}: {_CHAPTER_TITLES[index]}"
            section = chapter
            text = page.text
            headings = [h for h in page.topic_headings or []
                        if not h.startswith(("CHAPTER ", "PART"))]
            if number in _CHAPTER_STARTS:
                title_blocks = 2 if number in (8, 29, 40) else 1
                text, headings = _rebuild_opening(page, chapter, title_blocks, True)

        prepared.append(replace(page, text=text, chapter=chapter, section=section,
                                lines=text.splitlines(), topic_headings=headings))
    return prepared

"""Prepare the supplied 128-page Peale PDF for chapter-aware search."""

import re
from dataclasses import replace

from ingestion.pdf_processor import Page


# Physical PDF pages for this edition. Chapter headings often appear after
# the previous chapter's final paragraphs on the same page.
_CHAPTERS = (
    (2, "Believe in Yourself"),
    (10, "A Peaceful Mind Generates Power"),
    (18, "How to Have Constant Energy"),
    (24, "Try Prayer Power"),
    (33, "How to Create Your Own Happiness"),
    (41, "Stop Fuming and Fretting"),
    (49, "Expect the Best and Get It"),
    (59, "I Don’t Believe in Defeat"),
    (67, "How to Break the Worry Habit"),
    (73, "Power to Solve Personal Problems"),
    (80, "How to Use Faith in Healing"),
    (88, "When Vitality Sags, Try This Health Formula"),
    (94, "The Inflow of New Thoughts Can Remake You"),
    (102, "Relax for Easy Power"),
    (108, "How to Get People to Like You"),
    (114, "Prescription for Heartache"),
    (122, "How to Draw Upon Higher Power"),
)
_STARTS = {page: (index, title) for index, (page, title) in enumerate(_CHAPTERS, 1)}
_RUNNING_HEADER = "Power Of Positive Thinking by Noman V Peale"
_PAGE_LABEL = re.compile(r"(?:^|\s+)Page\s+\d+\Z", re.IGNORECASE)


def _clean_paragraphs(page: Page) -> list[str]:
    paragraphs = [part.strip() for part in page.text.split("\n\n")]
    if paragraphs and paragraphs[0].startswith(_RUNNING_HEADER):
        paragraphs[0] = paragraphs[0][len(_RUNNING_HEADER):].strip()
    return [cleaned for part in paragraphs
            if (cleaned := _PAGE_LABEL.sub("", part).strip())]


def _segment(page: Page, paragraphs: list[str], chapter: str) -> Page:
    text = "\n\n".join(paragraphs)
    return replace(page, text=text, lines=text.splitlines(), chapter=chapter,
                   section=chapter, topic_headings=None)


def prepare_positive_thinking(pages: list[Page]) -> list[Page]:
    """Keep introduction and 17 chapters with original PDF page numbers."""
    prepared: list[Page] = []
    chapter = "Introduction: What This Book Can Do for You"
    seen = set()
    for page in pages:
        paragraphs = _clean_paragraphs(page)
        if page.page_num in _STARTS:
            index, title = _STARTS[page.page_num]
            heading_at = next((i for i, part in enumerate(paragraphs)
                               if part.casefold() == title.casefold()), None)
            if heading_at is None:
                raise ValueError(f"Chapter {index} heading missing on PDF page {page.page_num}")
            if heading_at:
                prepared.append(_segment(page, paragraphs[:heading_at], chapter))
            chapter = f"Chapter {index}: {title}"
            paragraphs = paragraphs[heading_at:]
            seen.add(index)
        if paragraphs:
            prepared.append(_segment(page, paragraphs, chapter))
    if seen != set(range(1, 18)):
        raise ValueError("Unexpected chapter layout in The Power of Positive Thinking PDF")
    return prepared

"""Prepare the supplied 312-page Emotional Intelligence PDF for search."""

from bisect import bisect_right
from dataclasses import replace

from ingestion.pdf_processor import Page


# Physical PDF pages from this edition's table of contents. Part title pages
# contain no body text, so the following chapter starts a new search section.
_CHAPTERS = (
    (13, "What Are Emotions For?"),
    (22, "Anatomy of an Emotional Hijacking"),
    (37, "When Smart Is Dumb"),
    (49, "Know Thyself"),
    (58, "Passion's Slaves"),
    (78, "The Master Aptitude"),
    (94, "The Roots of Empathy"),
    (108, "The Social Arts"),
    (123, "Intimate Enemies"),
    (140, "Managing with Heart"),
    (154, "Mind and Medicine"),
    (175, "The Family Crucible"),
    (185, "Trauma and Emotional Relearning"),
    (199, "Temperament Is Not Destiny"),
    (212, "The Cost of Emotional Illiteracy"),
    (239, "Schooling the Emotions"),
)
_APPENDICES = (
    (264, "What Is Emotion?"),
    (266, "Hallmarks of the Emotional Mind"),
    (271, "The Neural Circuitry of Fear"),
    (274, "W. T. Grant Consortium: Active Ingredients of Prevention Programs"),
    (276, "The Self Science Curriculum"),
    (278, "Social and Emotional Learning: Results"),
)
_PART_PAGES = {12, 36, 122, 174, 211}
_CHAPTER_STARTS = tuple(page for page, _ in _CHAPTERS)
_APPENDIX_STARTS = tuple(page for page, _ in _APPENDICES)


def prepare_emotional_intelligence(pages: list[Page]) -> list[Page]:
    """Keep introduction, 16 chapters, and six appendices with PDF page numbers.

    Contents, part dividers, notes, and publisher matter are excluded. The
    generic detector mislabels appendices as Chapter 16, so this edition uses
    the PDF's contents page to assign chapter and appendix metadata.
    """
    prepared: list[Page] = []
    for page in pages:
        number = page.page_num
        if number < 7 or number >= 283 or number in _PART_PAGES:
            continue
        if number < _CHAPTER_STARTS[0]:
            chapter = "Introduction: Aristotle's Challenge"
        elif number < _APPENDIX_STARTS[0]:
            index = bisect_right(_CHAPTER_STARTS, number) - 1
            chapter = f"Chapter {index + 1}: {_CHAPTERS[index][1]}"
        else:
            index = bisect_right(_APPENDIX_STARTS, number) - 1
            chapter = f"Appendix {chr(ord('A') + index)}: {_APPENDICES[index][1]}"

        headings = [heading for heading in page.topic_headings or []
                    if not heading.startswith(("APPENDIX ", "PART "))
                    and heading != chapter.split(": ", 1)[-1]]
        prepared.append(replace(page, chapter=chapter, section=chapter,
                                topic_headings=headings))
    return prepared

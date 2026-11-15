"""Normalize generated citations against the passages actually retrieved."""

import re
from typing import Any

_CITATION = re.compile(
    r"[\[(]?\bChapter\s+(\d+)(?:\s*:[^,\n)\]]*)?,\s*"
    r"(?:p\.?|pages?)\s*(\d+)(?:\s*-\s*\d+)?[)\]]?",
    re.IGNORECASE,
)
_CHAPTER_NUMBER = re.compile(r"\bChapter\s+(\d+)\b", re.IGNORECASE)
_CHAPTER_ONLY = re.compile(r"\(Chapter\s+(\d+)\)", re.IGNORECASE)
_PAGE_ONLY = re.compile(r"\(p\.?\s*(\d+)\)", re.IGNORECASE)
_WEB_CITATION = re.compile(r"\[(\d{1,2})\]")


def filter_web_citations(answer: str, sources: list[dict[str, Any]]) -> str:
    """Remove numbered web citations absent from the returned search results."""
    valid = {int(source["index"]) for source in sources
             if source.get("kind") == "web" and str(source.get("index", "")).isdigit()}
    cleaned = _WEB_CITATION.sub(
        lambda match: match.group() if int(match.group(1)) in valid else "", answer
    )
    return re.sub(r"\s+([.!?,;:])", r"\1", re.sub(r" {2,}", " ", cleaned)).strip()


def _source_citation(source: dict[str, Any]) -> tuple[str, int, int] | None:
    metadata = source.get("metadata") or {}
    chapter = str(metadata.get("chapter") or "").strip()
    match = _CHAPTER_NUMBER.search(chapter)
    if chapter.isdecimal():
        chapter_number = chapter
    elif match:
        chapter_number = match.group(1)
    else:
        return None

    try:
        page_start = int(metadata["page_start"])
        page_end = int(metadata["page_end"])
    except (KeyError, TypeError, ValueError):
        return None
    if page_start < 1 or page_end < page_start:
        return None
    return chapter_number, page_start, page_end


def format_cited_answer(
    answer: str, sources: list[dict[str, Any]], append_fallback: bool = True
) -> str:
    """Keep only citations supported by retrieved chapter and page metadata."""
    allowed = [citation for source in sources if (citation := _source_citation(source))]
    page_ranges = []
    for source in sources:
        if source.get("book") not in ("tiny_habits", "power_of_habit", "power_of_now", "little_book_of_stoicism", "five_second_rule", "emotional_intelligence", "art_of_thinking_clearly", "positive_thinking", "subconscious_mind"):
            continue
        metadata = source.get("metadata") or {}
        try:
            start, end = int(metadata["page_start"]), int(metadata["page_end"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= start <= end:
            page_ranges.append((start, end))
    valid_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal valid_count
        chapter, page = match.group(1), int(match.group(2))
        if any(number == chapter and start <= page <= end for number, start, end in allowed):
            valid_count += 1
            return f"(Chapter {chapter}, p.{page})"
        return ""

    cleaned = _CITATION.sub(replace, answer)

    def replace_chapter_only(match: re.Match[str]) -> str:
        nonlocal valid_count
        chapter = match.group(1)
        for number, start, _ in allowed:
            if number == chapter:
                valid_count += 1
                return f"(Chapter {chapter}, p.{start})"
        return ""

    cleaned = _CHAPTER_ONLY.sub(replace_chapter_only, cleaned).strip()

    def replace_page_only(match: re.Match[str]) -> str:
        nonlocal valid_count
        page = int(match.group(1))
        if any(start <= page <= end for start, end in page_ranges):
            valid_count += 1
            return f"(p.{page})"
        return ""

    cleaned = _PAGE_ONLY.sub(replace_page_only, cleaned)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.!?,;:])", r"\1", cleaned)
    if valid_count or (not allowed and not page_ranges) or not cleaned or not append_fallback:
        return cleaned

    if not allowed:
        page = page_ranges[0][0]
        citation = f" (p.{page})"
        if cleaned[-1] in ".!?":
            return f"{cleaned[:-1]}{citation}{cleaned[-1]}"
        return cleaned + citation

    chapter, page, _ = allowed[0]
    citation = f" (Chapter {chapter}, p.{page})"
    if cleaned[-1] in ".!?":
        return f"{cleaned[:-1]}{citation}{cleaned[-1]}"
    return cleaned + citation

"""Chunk the Bookey Tiny Habits PDF according to its actual section layout."""

import html
import re

from ingestion.chunker import _ParagraphBlock, _accumulate_chunks, _finalize_chunk
from ingestion.pdf_processor import Page

_CHAPTER = re.compile(r"^Chapter\s+(\d{1,2})\b", re.IGNORECASE)
_QUESTION = re.compile(r"^\d+\.\s*Question\s*$", re.IGNORECASE)
_ANSWER = re.compile(r"\bAnswer\s*:\s*", re.IGNORECASE)
_TITLE_CONNECTORS = {"a", "an", "and", "as", "for", "from", "in", "of", "on", "or", "the", "to", "vs", "with"}


def _is_summary_heading(text: str) -> bool:
    """Ignore body fragments that the Bookey PDF renders in heading-sized type."""
    words = re.findall(r"[A-Za-z]+", text)
    return bool(words) and all(
        word[0].isupper() for word in words if word.lower() not in _TITLE_CONNECTORS
    )


def _clean_paragraph(text: str) -> str:
    text = html.unescape(re.sub(r"</?em>", "", text, flags=re.IGNORECASE))
    return re.sub(r"\s+", " ", text).strip()


def _chapter_titles(pages: list[Page]) -> dict[int, str]:
    """Use the PDF's contents page for stable titles across summaries and Q&A."""
    titles = {}
    for page in pages:
        if "Summary Content List" not in page.text:
            continue
        paragraphs = [p.strip() for p in page.text.split("\n\n")]
        for index, paragraph in enumerate(paragraphs):
            match = re.match(r"Chapter\s+(\d{1,2})\s*:\s*(.+)", paragraph.strip())
            if match:
                title = _clean_paragraph(match.group(2))
                if index + 1 < len(paragraphs) and re.fullmatch(r"[A-Z][A-Z ]{2,30}", paragraphs[index + 1]):
                    title += " " + paragraphs[index + 1]
                titles[int(match.group(1))] = re.sub(r"\s+", " ", title).strip()
        break
    return titles


def chunk_bookey_summary(
    pages: list[Page], chunk_size: int, chunk_overlap: int
) -> list:
    """Index each summary topic and complete Q&A pair, excluding quiz material.

    The PDF has four distinct parts: chapter summaries, selected quotes,
    numbered Q&A, and a true/false quiz. The quiz has false statements without
    answers, so it must never become retrieval context.
    """
    titles = _chapter_titles(pages)

    def chapter_label(number: int) -> str:
        title = titles.get(number)
        return f"Chapter {number}: {title}" if title else f"Chapter {number}"

    summary_blocks: list[_ParagraphBlock] = []
    quote_items: list[tuple[str, str, int, int]] = []
    quote_parts: list[tuple[str, int]] = []
    quote_start = 0
    quote_chapter: str | None = None
    qa_chunks = []
    mode = "summary"
    chapter: str | None = None
    section: str | None = None
    qa_parts: list[tuple[str, int]] = []
    qa_start = 0
    qa_chapter: str | None = None

    def finish_quote() -> None:
        nonlocal quote_parts, quote_start
        if quote_parts and quote_chapter:
            quote_items.append((
                _clean_paragraph(" ".join(text for text, _ in quote_parts)),
                quote_chapter,
                quote_start,
                quote_parts[-1][1],
            ))
        quote_parts = []
        quote_start = 0

    def finish_question() -> None:
        nonlocal qa_parts, qa_start
        if not qa_parts:
            return
        combined = _clean_paragraph(" ".join(text for text, _ in qa_parts))
        answer_match = _ANSWER.search(combined)
        if answer_match:
            question = combined[:answer_match.start()].strip()
            answer = combined[answer_match.end():].strip()
            if question and answer:
                qa_chunks.append(_finalize_chunk(
                    f"Question: {question}\nAnswer: {answer}",
                    qa_chapter,
                    question[:120],
                    qa_start,
                    qa_parts[-1][1],
                ))
        qa_parts = []
        qa_start = 0

    for page in pages:
        text = page.text
        if "Tiny Habits Quiz and Test" in text:
            finish_question()
            break
        if "Tiny Habits Questions" in text:
            finish_quote()
            mode = "qa"
            chapter = None
        elif "Best Quotes from Tiny Habits" in text:
            mode = "quotes"
            chapter = None

        # Cover, advertisements, and contents are navigation, not source claims.
        if page.page_num < 3 or "Summary Content List" in text:
            continue

        headings = {_clean_paragraph(h) for h in page.topic_headings or []}
        for raw in text.split("\n\n"):
            paragraph = _clean_paragraph(raw)
            if not paragraph:
                continue
            if paragraph.startswith((
                "Install Bookey App", "Written by Bookey", "Check more about",
                "Listen Tiny Habits", "Best Quotes from Tiny Habits",
                "Tiny Habits Questions View on Bookey", "Tiny Habits Quiz and Test",
            )) or paragraph == "Audio":
                continue

            chapter_match = _CHAPTER.match(paragraph)
            if chapter_match:
                finish_question()
                finish_quote()
                chapter = chapter_label(int(chapter_match.group(1)))
                section = "Summary" if mode == "summary" else "Selected quotes"
                continue

            if mode == "qa":
                if _QUESTION.fullmatch(paragraph):
                    finish_question()
                    qa_start = page.page_num
                    qa_chapter = chapter
                elif qa_start:
                    qa_parts.append((paragraph, page.page_num))
                continue

            if mode == "quotes":
                if re.match(r"^\d+\.", paragraph):
                    finish_quote()
                    quote_start = page.page_num
                    quote_chapter = chapter
                if quote_start:
                    quote_parts.append((paragraph, page.page_num))
                continue

            if paragraph == "Section Summary" or paragraph.startswith("Summary of Chapter"):
                continue
            if (
                paragraph in headings
                and len(paragraph) <= 90
                and not paragraph.endswith((".", "?", "!"))
                and (
                    _is_summary_heading(paragraph)
                    or paragraph in {"About the book", "About the author"}
                )
            ):
                section = paragraph
            summary_blocks.append(_ParagraphBlock(
                paragraph, page.page_num, chapter, section
            ))

    finish_question()
    finish_quote()
    chunks = []
    # This PDF is a short Bookey summary. Index its dense summary and quote
    # passages at finer granularity while leaving each Q&A answer complete.
    summary_size = min(chunk_size, 260)
    summary_overlap = 0
    if summary_blocks:
        summary_chunks = _accumulate_chunks(summary_blocks, summary_size, summary_overlap)
        chunks.extend(
            chunk for index, chunk in enumerate(summary_chunks)
            if not (
                index > 0
                and chunk.chapter == summary_chunks[index - 1].chapter
                and chunk.section == summary_chunks[index - 1].section
                and summary_chunks[index - 1].text.endswith(chunk.text)
            )
        )

    quote_group: list[tuple[str, str, int, int]] = []
    def finish_quote_group() -> None:
        nonlocal quote_group
        if quote_group:
            chunks.append(_finalize_chunk(
                "\n\n".join(item[0] for item in quote_group),
                quote_group[0][1], "Selected quotes",
                quote_group[0][2], quote_group[-1][3],
            ))
            quote_group = []

    for item in quote_items:
        group_length = sum(len(quote[0]) + 2 for quote in quote_group)
        if quote_group and (item[1] != quote_group[0][1] or group_length + len(item[0]) > summary_size):
            finish_quote_group()
        quote_group.append(item)
    finish_quote_group()
    chunks.extend(qa_chunks)
    return chunks

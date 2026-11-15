"""Mark the indexed source passage on its original PDF page."""

import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import pymupdf

import config

_CHUNK_ID = re.compile(r"[0-9a-f]{12}(?:_[1-9][0-9]*)?\Z")


@lru_cache(maxsize=9)
def _chunk_index(path: str, modified_ns: int) -> dict[str, dict]:
    """Cache inspection copies and invalidate them after re-ingestion."""
    chunks = json.loads(Path(path).read_text(encoding="utf-8"))
    return {chunk["chunk_id"]: chunk for chunk in chunks}


def source_chunk(book: str, page: int | None, chunk_id: str) -> dict | None:
    """Find a chunk, checking its cited PDF page when one is supplied."""
    if book not in config.BOOKS or not _CHUNK_ID.fullmatch(chunk_id):
        return None
    path = config.book_chunks_path(book)
    if not path.is_file():
        return None
    chunk = _chunk_index(str(path), path.stat().st_mtime_ns).get(chunk_id)
    if chunk is None:
        return None
    if page is not None and not int(chunk["page_start"]) <= page <= int(chunk["page_end"]):
        return None
    return chunk


def _token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _highlight(page: pymupdf.Page, rect: pymupdf.Rect) -> None:
    annotation = page.add_highlight_annot(rect)
    annotation.set_colors(stroke=(1, 0.88, 0))
    annotation.set_opacity(0.6)
    annotation.update()


def highlight_source(page: pymupdf.Page, chunk: dict) -> int:
    """Highlight matching lines from this chunk plus its topic on the page.

    Word-sequence matching tolerates PDF line breaks and chunk whitespace.
    Only long contiguous matches are marked, avoiding isolated common words.
    """
    source_text = str(chunk.get("text", ""))
    question_and_answer = re.search(r"(?is)^Question:.*?\bAnswer:\s*(.+)$", source_text)
    if question_and_answer:
        source_text = question_and_answer.group(1)
    words = page.get_text("words", sort=True)
    page_words = [(word, _token(word[4])) for word in words if _token(word[4])]
    chunk_words = [_token(word) for word in source_text.split()]
    chunk_words = [word for word in chunk_words if word]
    matches = SequenceMatcher(
        None, [word for _, word in page_words], chunk_words, autojunk=False
    ).get_matching_blocks()

    marked = 0
    minimum_match = max(5, min(12, len(chunk_words) // 10))
    for match in matches:
        if match.size < minimum_match:
            continue
        lines: dict[tuple[int, int], pymupdf.Rect] = {}
        for word, _ in page_words[match.a:match.a + match.size]:
            line = (word[5], word[6])
            rect = pymupdf.Rect(word[:4])
            lines[line] = lines[line] | rect if line in lines else rect
            marked += 1
        if question_and_answer:
            for word, _ in page_words:
                line = (word[5], word[6])
                if line in lines and word[4].casefold().startswith("answer:"):
                    lines[line] |= pymupdf.Rect(word[:4])
        for rect in lines.values():
            _highlight(page, rect)

    topic = "" if question_and_answer else str(chunk.get("section") or chunk.get("chapter") or "").strip()
    if topic:
        for rect in page.search_for(topic)[:3]:
            _highlight(page, rect)
            marked += 1
    return marked

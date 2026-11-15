"""Choose the most relevant indexed book before answering an auto-mode query."""

import logging
from typing import Any

from core.book_summaries import BOOK_SUMMARIES
from core.query_spelling import repair_book_typos

logger = logging.getLogger(__name__)

_EXPLICIT_BOOK_NAMES = {
    "atomic_habits": ("atomic habits", "james clear"),
    "tiny_habits": ("tiny habits", "bj fogg", "b. j. fogg"),
    "power_of_habit": ("the power of habit", "power of habit", "charles duhigg"),
    "power_of_now": ("the power of now", "power of now", "eckhart tolle"),
    "little_book_of_stoicism": ("the little book of stoicism", "little book of stoicism", "jonas salzgeber"),
    "five_second_rule": ("the 5 second rule", "5 second rule", "mel robbins"),
    "emotional_intelligence": ("emotional intelligence", "daniel goleman"),
    "art_of_thinking_clearly": ("the art of thinking clearly", "art of thinking clearly", "rolf dobelli"),
    "positive_thinking": ("the power of positive thinking", "power of positive thinking", "norman vincent peale", "norman peale"),
    "subconscious_mind": ("the power of your subconscious mind", "power of your subconscious mind", "joseph murphy"),
}


def choose_book(question: str, engines: dict[str, Any], reranker: Any) -> str | None:
    """Score book summaries and real passages, then choose the strongest book.

    Summaries can break close passage-score ties, but a book must have a
    retrieved passage to win. The answer pipeline uses only that book's chunks.
    """
    search_question = repair_book_typos(question)
    normalized = search_question.casefold()
    named_books = [book for book, names in _EXPLICIT_BOOK_NAMES.items()
                   if book in engines and any(name in normalized for name in names)]
    if len(named_books) == 1:
        return named_books[0]

    candidates: list[dict[str, Any]] = []
    for book, engine in engines.items():
        try:
            passages = engine.retriever.retrieve(search_question, top_k=5)
            candidates.extend(dict(passage, book=book) for passage in passages)
        except Exception:
            logger.warning("Book selection retrieval failed for %s.", book, exc_info=True)

    if not candidates:
        return None

    summaries = [
        {"chunk_id": f"summary:{book}", "book": book, "text": BOOK_SUMMARIES[book],
         "routing_summary": True}
        for book in engines if book in BOOK_SUMMARIES
    ]
    ranked = reranker.rerank(search_question, [*candidates, *summaries],
                            top_n=len(candidates) + len(summaries))
    passage_scores: dict[str, float] = {}
    summary_scores: dict[str, float] = {}
    for item in ranked:
        book = item["book"]
        score = float(item["rerank_score"])
        if item.get("routing_summary"):
            summary_scores[book] = score
        else:
            passage_scores[book] = max(score, passage_scores.get(book, float("-inf")))

    if not passage_scores:
        return None
    best_summary = max(summary_scores.values(), default=0.0)

    def combined_score(book: str) -> float:
        # A summary only nudges close decisions; passage evidence dominates.
        summary_gap = max(0.0, best_summary - summary_scores.get(book, best_summary))
        return passage_scores[book] - min(summary_gap, 2.0) * 0.25

    selected = max(passage_scores, key=combined_score)
    logger.info("Auto selected %s from summary and passage relevance.", selected)
    return selected

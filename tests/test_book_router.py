"""Auto book selection compares actual retrieved passages."""

from types import SimpleNamespace
from unittest.mock import Mock

from core.book_router import choose_book
from core.book_summaries import BOOK_SUMMARIES


def _engine(book: str, passage: str):
    retriever = Mock()
    retriever.retrieve.return_value = [{
        "chunk_id": book,
        "text": passage,
        "metadata": {"chapter": "Chapter 1", "page_start": 10, "page_end": 10},
    }]
    return SimpleNamespace(retriever=retriever)


def test_selects_book_with_highest_reranked_passage():
    engines = {
        "atomic_habits": _engine("atomic_habits", "Four laws of behavior change."),
        "tiny_habits": _engine("tiny_habits", "Anchor moments and celebration."),
        "power_of_habit": _engine("power_of_habit", "Keystone habits affect routines."),
    }
    reranker = Mock()
    def score(question, chunks, top_n):
        assert question == "What are keystone habits?"
        scores = {"atomic_habits": 1.0, "tiny_habits": 1.5, "power_of_habit": 4.0}
        return sorted(
            (dict(chunk, rerank_score=scores[chunk["book"]]) for chunk in chunks),
            key=lambda chunk: chunk["rerank_score"], reverse=True,
        )

    reranker.rerank.side_effect = score

    assert choose_book("What are keystone habits?", engines, reranker) == "power_of_habit"
    assert all(engine.retriever.retrieve.call_count == 1 for engine in engines.values())
    ranked_input = reranker.rerank.call_args.args[1]
    assert {chunk["book"] for chunk in ranked_input} == set(engines)
    assert {chunk["book"] for chunk in ranked_input if chunk.get("routing_summary")} == set(engines)
    assert len(BOOK_SUMMARIES) == 10


def test_auto_book_search_repairs_typo_before_retrieval():
    engines = {"five_second_rule": _engine("five_second_rule", "Take action despite hesitation.")}
    reranker = Mock()
    reranker.rerank.side_effect = lambda question, chunks, top_n: [
        dict(chunk, rerank_score=1.0) for chunk in chunks
    ]

    assert choose_book("what is the minimum prod to overcme a hbit",
                       engines, reranker) == "five_second_rule"
    engines["five_second_rule"].retriever.retrieve.assert_called_once_with(
        "what is the minimum prod to overcome a habit", top_k=5
    )
    assert reranker.rerank.call_args.args[0] == "what is the minimum prod to overcome a habit"


def test_summary_resolves_close_passage_scores_but_cannot_replace_a_passage():
    engines = {
        "atomic_habits": _engine("atomic_habits", "Habits and identity."),
        "tiny_habits": _engine("tiny_habits", "Anchor moments follow prompts."),
    }
    reranker = Mock()

    def score(question, chunks, top_n):
        scores = {
            ("atomic_habits", False): 3.1,
            ("tiny_habits", False): 3.0,
            ("atomic_habits", True): 1.0,
            ("tiny_habits", True): 3.0,
        }
        return [dict(chunk, rerank_score=scores[chunk["book"],
                                                  bool(chunk.get("routing_summary"))])
                for chunk in chunks]

    reranker.rerank.side_effect = score
    assert choose_book("How do anchor moments work?", engines, reranker) == "tiny_habits"

    engines["tiny_habits"].retriever.retrieve.return_value = []
    assert choose_book("How do anchor moments work?", engines, reranker) == "atomic_habits"


def test_explicit_book_request_stays_with_named_book():
    engines = {"tiny_habits": _engine("tiny_habits", "Anchor moments")}

    assert choose_book("In Tiny Habits, what is an anchor?", engines, Mock()) == "tiny_habits"
    engines["tiny_habits"].retriever.retrieve.assert_not_called()

    engines["power_of_now"] = _engine("power_of_now", "Present moment awareness")
    assert choose_book("In The Power of Now, what is presence?", engines, Mock()) == "power_of_now"
    engines["power_of_now"].retriever.retrieve.assert_not_called()
    engines["little_book_of_stoicism"] = _engine(
        "little_book_of_stoicism", "Stoic dichotomy of control")
    assert choose_book("In The Little Book of Stoicism, what can I control?",
                       engines, Mock()) == "little_book_of_stoicism"
    engines["little_book_of_stoicism"].retriever.retrieve.assert_not_called()
    engines["five_second_rule"] = _engine("five_second_rule", "Count backward to act")
    assert choose_book("In The 5 Second Rule, why count backward?",
                       engines, Mock()) == "five_second_rule"
    engines["five_second_rule"].retriever.retrieve.assert_not_called()
    engines["emotional_intelligence"] = _engine("emotional_intelligence", "Emotional hijacking")
    assert choose_book("In Emotional Intelligence, what is an emotional hijack?",
                       engines, Mock()) == "emotional_intelligence"
    engines["emotional_intelligence"].retriever.retrieve.assert_not_called()
    engines["art_of_thinking_clearly"] = _engine(
        "art_of_thinking_clearly", "Survivorship bias")
    assert choose_book("In The Art of Thinking Clearly, what is survivorship bias?",
                       engines, Mock()) == "art_of_thinking_clearly"
    engines["art_of_thinking_clearly"].retriever.retrieve.assert_not_called()
    engines["positive_thinking"] = _engine("positive_thinking", "Break the worry habit")
    assert choose_book("In The Power of Positive Thinking, how can I stop worrying?",
                       engines, Mock()) == "positive_thinking"
    engines["positive_thinking"].retriever.retrieve.assert_not_called()
    engines["subconscious_mind"] = _engine("subconscious_mind", "Conscious and subconscious mind")
    assert choose_book("In The Power of Your Subconscious Mind, what is suggestion?",
                       engines, Mock()) == "subconscious_mind"
    engines["subconscious_mind"].retriever.retrieve.assert_not_called()

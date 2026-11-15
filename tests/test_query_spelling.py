"""Book-term spelling repair stays narrow enough for scope checks."""

import pytest

from core.query_spelling import repair_book_typos
from core.scope_checker import is_in_scope


@pytest.mark.parametrize(("question", "expected"), [
    ("what is the minimum prod to overcme a hbit",
     "what is the minimum prod to overcome a habit"),
    ("How do I stop procastination?", "How do I stop procrastination?"),
    ("What is a promt?", "What is a prompt?"),
    ("How do I change a habti?", "How do I change a habit?"),
    ("how lng it takes to get over a hbit?", "how long it takes to get over a habit?"),
])
def test_repairs_unambiguous_book_terms(question, expected):
    assert repair_book_typos(question) == expected


def test_misspelled_habit_question_stays_in_book_scope():
    assert is_in_scope("what is the minimum prod to overcme a hbit", "five_second_rule")


@pytest.mark.parametrize("question", [
    "How do I create a Next.js app?",
    "What is the capital of France?",
    "What is a rabbit?",
])
def test_unrelated_questions_are_not_corrected_into_book_topics(question):
    assert repair_book_typos(question) == question
    assert not is_in_scope(question, "five_second_rule")

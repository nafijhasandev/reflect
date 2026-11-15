"""Conservative spelling repair for common terms in the indexed books."""

import re

_BOOK_TERMS = frozenset({
    "affirmation", "affirmations", "amygdala", "anchor", "anchors",
    "anxiety", "atomic", "attention", "awareness", "behavior",
    "behaviors", "behaviour", "behaviours", "belief", "beliefs",
    "bundling", "celebration", "conscious", "consistency", "control",
    "courage", "craving", "cravings", "discipline", "emotion",
    "emotional", "emotions", "empathy", "environment", "exercise",
    "fallacy", "forgiveness", "habit", "habits", "happiness",
    "identity", "keystone", "meditation", "motivation", "motivated",
    "overcome", "positive", "presence", "procrastination", "prompt",
    "prompts", "reading", "resilience", "reward", "rewards",
    "routine", "routines", "stoicism", "subconscious", "suggestion",
    "thinking", "visualization", "willpower",
})
_WORD = re.compile(r"\b[A-Za-z]{4,}\b")


def _edit_distance(left: str, right: str, limit: int) -> int:
    """Return a bounded edit distance, counting adjacent swaps as one typo."""
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    if len(left) == len(right):
        for index in range(len(left) - 1):
            if (left[:index] + left[index + 1] + left[index]
                    + left[index + 2:] == right):
                return 1
    previous = list(range(len(right) + 1))
    for row, char in enumerate(left, 1):
        current = [row]
        for column, other in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (char != other),
            ))
        previous = current
    return previous[-1]


def repair_book_typos(question: str) -> str:
    """Repair a word only when one book term is its unique close match."""
    question = re.sub(r"\bhow\s+lng\b", "how long", question, flags=re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        word = match.group()
        lower = word.casefold()
        if lower in _BOOK_TERMS:
            return word
        limit = 1 if len(lower) < 9 else 2
        candidates = [term for term in _BOOK_TERMS
                      if _edit_distance(lower, term, limit) <= limit]
        if not candidates:
            return word
        best_distance = min(_edit_distance(lower, term, limit) for term in candidates)
        best = [term for term in candidates
                if _edit_distance(lower, term, limit) == best_distance]
        if len(best) != 1:
            return word
        replacement = best[0]
        return replacement.capitalize() if word[0].isupper() else replacement

    return _WORD.sub(replace, question)

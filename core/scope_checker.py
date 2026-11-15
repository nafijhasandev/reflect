"""Fast check for whether a question may benefit from indexed book passages."""

import re
from functools import lru_cache

from core.query_spelling import repair_book_typos

_BOOK_PHRASES = (
    "atomic habits",
    "james clear",
    "the book",
    "this book",
    "chapter ",
    "two-minute rule",
    "two minute rule",
    "2-minute rule",
    "2 minute rule",
    "four laws",
    "1 percent better",
    "one percent better",
    "habit stacking",
    "temptation bundling",
    "marginal gains",
    "small changes",
    "small improvements",
    "tiny changes",
)

_BOOK_WORDS = {
    "habit", "habits", "routine", "routines", "cue", "cues", "craving",
    "cravings", "reward", "rewards", "behavior", "behaviour", "identity",
    "goals", "goal", "systems", "system", "motivation", "motivated",
    "procrastination", "procrastinating", "discipline", "consistency",
    "repetition", "environment", "exercise", "reading", "meditation",
    "goldilocks", "diderot", "plateau", "willpower", "selfcontrol", "cycling",
}


@lru_cache(maxsize=1)
def _dobelli_topics() -> tuple[str, ...]:
    """Recognize every named bias and chapter heading in the supplied PDF."""
    from ingestion.art_of_thinking_clearly import _chapter_entries

    try:
        entries = _chapter_entries()
    except (FileNotFoundError, ValueError):
        return ()
    return tuple(
        re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
        for _, chapter, heading in entries
        for title in (chapter.split(": ", 1)[1], heading,
                      re.sub(r"^why\s+", "", heading, flags=re.IGNORECASE))
    )


def is_in_scope(question: str, book: str = "atomic_habits") -> bool:
    """Allow book-related questions without searching document sources."""
    normalized = repair_book_typos(question).casefold()
    if book == "subconscious_mind" and any(phrase in normalized for phrase in (
        "power of your subconscious mind", "joseph murphy", "subconscious",
        "conscious mind", "suggestion", "affirmation", "visualization",
        "mental imagery", "mental healing", "scientific prayer", "belief",
        "treasure house within", "miracle-working", "mind works",
        "wealth", "success", "sleep", "marital", "happiness",
        "forgiveness", "mental blocks", "remove fear", "stay young",
        "harmonious human relations", "life-ward", "lifeward",
    )):
        return True
    if book == "positive_thinking" and any(phrase in normalized for phrase in (
        "power of positive thinking", "norman vincent peale", "norman peale",
        "positive thinking", "believe in yourself", "peaceful mind",
        "constant energy", "prayer power", "create your own happiness",
        "fuming", "fretting", "expect the best", "defeat", "worry habit",
        "personal problems", "faith in healing", "vitality", "new thoughts",
        "relax for easy power", "people to like you", "heartache",
        "higher power", "self-confidence", "self confidence", "confidence",
        "prayer", "faith", "serenity", "peace of mind", "negative thoughts",
        "worry", "worried", "worrying", "think positively",
    )):
        return True
    if book == "art_of_thinking_clearly":
        words = " " + re.sub(r"[^a-z0-9]+", " ", normalized).strip() + " "
        if any(f" {topic} " in words for topic in _dobelli_topics()):
            return True
    if book == "art_of_thinking_clearly" and any(phrase in normalized for phrase in (
        "art of thinking clearly", "rolf dobelli", "thinking error",
        "cognitive bias", "survivorship bias", "confirmation bias",
        "sunk cost", "social proof", "overconfidence", "anchoring",
        "framing", "loss aversion", "planning fallacy", "news illusion",
        "swimmer's body", "swimmer’s body", "groupthink", "availability bias",
        "reciprocity", "outcome bias", "base-rate", "base rate",
        "decision making", "decision-making", "reasoning error",
        "fallacy", "bias", "better thinking",
    )):
        return True
    if book == "emotional_intelligence" and any(phrase in normalized for phrase in (
        "emotional intelligence", "daniel goleman", "emotional brain",
        "emotional hijack", "amygdala", "self-awareness", "self awareness",
        "empathy", "social arts", "emotional literacy", "emotional learning",
        "emotional mind", "emotional skill", "managing emotion", "temperament",
        "trauma", "motivation", "self-control", "emotional development",
        "passion", "feeling", "emotion", "iq",
    )):
        return True
    if book == "five_second_rule" and any(phrase in normalized for phrase in (
        "5 second rule", "five second rule", "mel robbins", "5-4-3-2-1",
        "5 4 3 2 1", "countdown", "counting backward", "count backwards",
        "counting backwards", "five seconds", "everyday courage", "hesitat",
        "wake up challenge", "wake-up challenge", "procrastination",
        "productivity", "worry", "anxiety", "fear", "confidence",
        "passion", "relationship",
    )):
        return True
    if book == "little_book_of_stoicism" and any(phrase in normalized for phrase in (
        "stoic", "stoicism", "salzgeber", "dichotomy of control", "virtue",
        "negative visualization", "eudaimonia", "equanimity", "stoic sage",
        "epictetus", "marcus aurelius", "seneca", "zeno", "reserve clause",
        "insult", "grief", "anger", "morning routine", "evening routine",
        "voluntary discomfort", "resilience", "control", "judgment",
        "acceptance", "troubling emotions",
    )):
        return True
    if book == "power_of_now" and any(phrase in normalized for phrase in (
        "power of now", "eckhart tolle", "the now", "present moment",
        "presence", "consciousness", "thinking mind", "suffering",
        "pain-body", "pain body", "psychological time", "inner body",
        "surrender", "being", "ego", "unmanifested", "enlightenment",
    )):
        return True
    if book == "power_of_habit" and any(phrase in normalized for phrase in (
        "power of habit", "charles duhigg", "habit loop", "eugene pauly",
        "basal ganglia", "rat maze", "cue routine reward",
        "keystone habit", "tony dungy", "alcoa", "paul o'neill",
        "starbucks", "target", "rosa parks", "montgomery", "saddleback",
        "rick warren", "angie bachmann", "social movement",
    )):
        return True
    if book == "tiny_habits" and any(phrase in normalized for phrase in (
        "tiny habits", "bj fogg", "b. j. fogg", "fogg behavior model",
        "fogg behaviour model", "anchor moment", "shine", "celebration",
        "starter step", "golden behavior",
    )):
        return True
    if any(phrase in normalized for phrase in _BOOK_PHRASES):
        return True
    words = set(re.findall(r"[a-z]+", normalized))
    return bool(words & _BOOK_WORDS)

"""Short, source-free replies to standalone greetings and courtesies."""

import re

_GREETINGS = {
    "hi", "hii", "hello", "helllo", "hey", "hiya", "hello there", "hi there",
    "hey there", "good morning", "good afternoon", "good evening",
    "how are you", "how are you doing",
}
_THANKS = {
    "thanks", "thank you", "thank you so much", "thank you very much",
    "thanks a lot", "many thanks", "thx", "thank u", "appreciate it",
}
_REQUESTS = {"please", "pls", "please help", "can you help me", "could you help me"}


def social_reply(message: str, book: str = "auto") -> str | None:
    """Reply only when the whole message is conversational, not a book query."""
    normalized = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", message.casefold())).strip()
    if not normalized:
        return None
    invitation = "What would you like to know?"
    if normalized in _GREETINGS:
        return f"Hello! {invitation}"
    if normalized in _THANKS:
        return f"You're welcome! {invitation}"
    if normalized in _REQUESTS:
        return f"Of course. {invitation}"
    return None

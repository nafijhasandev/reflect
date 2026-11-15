"""Short routing summaries grounded in the supported PDFs.

These describe each book's central ideas and distinctive topics. They help
choose a book, but are never sent as answer context or used as citations.
Review them when replacing a PDF with a different edition or book.
"""

BOOK_SUMMARIES = {
    "atomic_habits": (
        "Atomic Habits by James Clear: small improvements compound and habits "
        "shape identity. Its four-step habit loop is cue, craving, response, "
        "reward. The four laws make a habit obvious, attractive, easy, and "
        "satisfying. Topics include habit stacking, environment design, the "
        "two-minute rule, tracking, and accountability."
    ),
    "tiny_habits": (
        "Tiny Habits by BJ Fogg: behavior happens when motivation, ability, "
        "and a prompt come together. Start with a tiny action after an existing "
        "anchor moment and celebrate to create positive emotion. Topics include "
        "the Fogg Behavior Model, golden behaviors, growing habits, and "
        "untangling bad habits."
    ),
    "power_of_habit": (
        "The Power of Habit by Charles Duhigg: the three-step habit loop is "
        "cue, routine, reward, with cravings helping sustain it. Habit change "
        "can replace a routine while keeping its cue and reward. Topics include "
        "keystone habits, willpower, organizational habits, consumer behavior, "
        "social movements, and the neurology of free will."
    ),
    "power_of_now": (
        "The Power of Now by Eckhart Tolle: presence and attention to the "
        "present moment help loosen identification with the thinking mind and "
        "the ego. Topics include psychological time, the pain-body, the inner "
        "body, conscious relationships, acceptance, and surrender."
    ),
    "little_book_of_stoicism": (
        "The Little Book of Stoicism by Jonas Salzgeber: practical Stoic "
        "philosophy for resilience, calm, and living with virtue. It explains "
        "the dichotomy of control, the Stoic Happiness Triangle, and negative "
        "emotions. Its 55 numbered practices include negative visualization, "
        "voluntary discomfort, morning and evening routines, handling grief "
        "and anger, kindness, and responding to insults."
    ),
    "five_second_rule": (
        "The 5 Second Rule by Mel Robbins: use a backward five-second "
        "countdown and physical movement to interrupt hesitation and act on "
        "goals. Topics include everyday courage, the wake-up challenge, "
        "health, productivity, procrastination, worry, anxiety, fear, "
        "confidence, passion, and relationships."
    ),
    "emotional_intelligence": (
        "Emotional Intelligence: Why It Can Matter More Than IQ by Daniel Goleman: "
        "how emotion and reason work together, emotional hijacking, self-awareness, "
        "managing emotions, motivation, empathy, and social skills. It applies "
        "emotional intelligence to relationships, work, and health, and examines "
        "childhood emotional development, trauma, temperament, and emotional literacy education."
    ),
    "art_of_thinking_clearly": (
        "The Art of Thinking Clearly by Rolf Dobelli: 99 short chapters on "
        "cognitive biases, reasoning errors, and better decisions. Topics "
        "include survivorship bias, confirmation bias, sunk cost fallacy, "
        "social proof, overconfidence, anchoring, framing, loss aversion, "
        "planning fallacy, and the news illusion."
    ),
    "positive_thinking": (
        "The Power of Positive Thinking by Norman Vincent Peale: practical "
        "religious techniques for confidence, peace of mind, energy, prayer, "
        "happiness, handling worry and defeat, solving personal problems, "
        "healing through faith, renewing thoughts, relationships, and drawing "
        "on a higher power."
    ),
    "subconscious_mind": (
        "The Power of Your Subconscious Mind by Joseph Murphy: the conscious "
        "and subconscious mind, belief, suggestion, visualization, prayer, "
        "and mental imagery. Its 20 chapters apply these ideas to healing, "
        "wealth, success, sleep, relationships, happiness, forgiveness, "
        "habits, fear, and aging."
    ),
}

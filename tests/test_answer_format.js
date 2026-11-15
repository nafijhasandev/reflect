const test = require("node:test");
const assert = require("node:assert/strict");
const AnswerFormat = require("../web/static/answer_format.js");

test("renders bold topic names and chapter citations", () => {
    assert.equal(
        AnswerFormat.formatHtml("**Habit stacking** builds on a cue.\n\nSee **Chapter 5**."),
        "<p><strong>Habit stacking</strong> builds on a cue.</p><p>See <strong>Chapter 5</strong>.</p>",
    );
});

test("renders markdown headings as bold text", () => {
    assert.equal(
        AnswerFormat.formatHtml("## The Four Laws\nMake it obvious."),
        "<p><strong>The Four Laws</strong>\nMake it obvious.</p>",
    );
});

test("bolds plain topic introductions and numbered labels", () => {
    assert.equal(
        AnswerFormat.formatHtml("The four laws are:\n\n1. The first law (Cue): Make it obvious."),
        "<p><strong>The four laws are:</strong></p><p><strong>1. The first law (Cue):</strong> Make it obvious.</p>",
    );
});

test("escapes model output before adding formatting", () => {
    assert.equal(
        AnswerFormat.formatHtml("**<script>alert('x')</script>** & details"),
        "<p><strong>&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;</strong> &amp; details</p>",
    );
});

test("links only citations supported by retrieved PDF pages", () => {
    const sources = [{ metadata: {
        chapter: "Chapter 5: The Best Way to Start a New Habit",
        section: "HABIT STACKING",
        page_start: 73,
        page_end: 75,
    } }];
    assert.equal(
        AnswerFormat.formatHtml("Use a cue (Chapter 5, p.74). Avoid guesses (Chapter 9, p.99).", sources),
        '<p>Use a cue <a class="citation-link" href="/book.pdf#page=74" data-pdf-page="74" data-pdf-start="73" data-pdf-end="75" data-pdf-topic="HABIT STACKING" target="_blank" rel="noopener noreferrer">(Chapter 5, p.74) <span class="citation-book">Atomic Habits</span></a>. Avoid guesses (Chapter 9, p.99).</p>',
    );
});

test("source links carry a safe topic and page for the side viewer", () => {
    const source = { metadata: {
        section: 'A "quoted" <topic>', page_start: 91,
    } };
    assert.equal(AnswerFormat.sourceTopic(source), 'A "quoted" <topic>');
    assert.equal(
        AnswerFormat.sourceLink(source),
        'href="/book.pdf#page=91" data-pdf-page="91" data-pdf-topic="A &quot;quoted&quot; &lt;topic&gt;" target="_blank" rel="noopener noreferrer"',
    );
    assert.equal(AnswerFormat.sourceLink({ metadata: { page_start: -1 } }), null);
    assert.equal(AnswerFormat.sourceTopic({ metadata: { section: "  " } }), "Atomic Habits");
});

test("source links include the indexed chunk for PDF highlighting", () => {
    const source = {
        book: "power_of_habit", chunk_id: "a1b2c3d4e5f6",
        metadata: { section: "The Habit Loop", page_start: 39 },
    };
    assert.match(AnswerFormat.sourceLink(source), /data-pdf-chunk="a1b2c3d4e5f6"/);
    assert.match(AnswerFormat.sourceLink(source), /href="\/source-page\.pdf\?book=power_of_habit&amp;chunk_id=a1b2c3d4e5f6"/);
    source.chunk_id = "a1b2c3d4e5f6_1";
    assert.match(AnswerFormat.sourceLink(source), /data-pdf-chunk="a1b2c3d4e5f6_1"/);
    source.chunk_id = 'bad" onload="alert(1)';
    assert.doesNotMatch(AnswerFormat.sourceLink(source), /data-pdf-chunk/);
});

test("rejects invalid source pages and keeps answer HTML escaped", () => {
    const sources = [{ metadata: { chapter: "Chapter 5", page_start: -1, page_end: 75 } }];
    assert.equal(AnswerFormat.sourcePage(sources[0]), null);
    assert.equal(
        AnswerFormat.formatHtml("<script>alert(1)</script> (Chapter 5, p.74)", sources),
        "<p>&lt;script&gt;alert(1)&lt;/script&gt; (Chapter 5, p.74)</p>",
    );
});

test("links Tiny Habits pages to its own PDF", () => {
    const source = { book: "tiny_habits", metadata: {
        section: "Anchor moments", page_start: 23, page_end: 24,
    } };
    assert.equal(
        AnswerFormat.formatHtml("Begin after an anchor (p.24).", [source]),
        '<p>Begin after an anchor <a class="citation-link" href="/book.pdf?book=tiny_habits#page=24" data-pdf-page="24" data-pdf-book="tiny_habits" data-pdf-start="23" data-pdf-end="24" data-pdf-topic="Anchor moments" target="_blank" rel="noopener noreferrer">(p.24) <span class="citation-book">Tiny Habits</span></a>.</p>',
    );
});

test("links Power of Habit citations to the full-book PDF", () => {
    const source = { book: "power_of_habit", metadata: {
        chapter: "Chapter 1: The Habit Loop", page_start: 23, page_end: 24,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Power of Habit");
    assert.equal(
        AnswerFormat.formatHtml("Habits have a loop (Chapter 1, p.23).", [source]),
        '<p>Habits have a loop <a class="citation-link" href="/book.pdf?book=power_of_habit#page=23" data-pdf-page="23" data-pdf-book="power_of_habit" data-pdf-start="23" data-pdf-end="24" data-pdf-topic="Chapter 1: The Habit Loop" target="_blank" rel="noopener noreferrer">(Chapter 1, p.23) <span class="citation-book">The Power of Habit</span></a>.</p>',
    );
});

test("links Power of Now citations to its PDF", () => {
    const source = { book: "power_of_now", metadata: {
        chapter: "Chapter 10: The Meaning of Surrender", page_start: 198, page_end: 198,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Power of Now");
    assert.match(
        AnswerFormat.formatHtml("Accept the Now (Chapter 10, p.198).", [source]),
        /href="\/book\.pdf\?book=power_of_now#page=198".*The Power of Now/,
    );
});

test("links Little Book of Stoicism citations to its PDF", () => {
    const source = { book: "little_book_of_stoicism", metadata: {
        chapter: "Chapter 6: Preparing Practices", section: "Practice 9: The Stoic Morning Routine",
        page_start: 112, page_end: 112,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Little Book of Stoicism");
    assert.match(
        AnswerFormat.formatHtml("Prepare for the day (Chapter 6, p.112).", [source]),
        /href="\/book\.pdf\?book=little_book_of_stoicism#page=112".*The Little Book of Stoicism/,
    );
});

test("links 5 Second Rule citations to its PDF", () => {
    const source = { book: "five_second_rule", metadata: {
        chapter: "Chapter 8: How to Start Using the Rule", page_start: 110, page_end: 110,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The 5 Second Rule");
    assert.match(
        AnswerFormat.formatHtml("Try the challenge (Chapter 8, p.110).", [source]),
        /href="\/book\.pdf\?book=five_second_rule#page=110".*The 5 Second Rule/,
    );
});

test("links Emotional Intelligence citations to its PDF", () => {
    const source = { book: "emotional_intelligence", metadata: {
        chapter: "Chapter 2: Anatomy of an Emotional Hijacking", page_start: 25, page_end: 25,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "Emotional Intelligence");
    assert.match(
        AnswerFormat.formatHtml("The amygdala can trigger a response (Chapter 2, p.25).", [source]),
        /href="\/book\.pdf\?book=emotional_intelligence#page=25".*Emotional Intelligence/,
    );
});

test("links Art of Thinking Clearly citations to its PDF", () => {
    const source = { book: "art_of_thinking_clearly", metadata: {
        chapter: "Chapter 5: Sunk Cost Fallacy", page_start: 22, page_end: 22,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Art of Thinking Clearly");
    assert.match(
        AnswerFormat.formatHtml("Past costs can distort choices (Chapter 5, p.22).", [source]),
        /href="\/book\.pdf\?book=art_of_thinking_clearly#page=22".*The Art of Thinking Clearly/,
    );
});

test("links Power of Positive Thinking citations to its PDF", () => {
    const source = { book: "positive_thinking", metadata: {
        chapter: "Chapter 9: How to Break the Worry Habit", page_start: 67, page_end: 67,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Power of Positive Thinking");
    assert.match(
        AnswerFormat.formatHtml("Practice faith rather than worry (Chapter 9, p.67).", [source]),
        /href="\/book\.pdf\?book=positive_thinking#page=67".*The Power of Positive Thinking/,
    );
});

test("links Power of Your Subconscious Mind citations to its PDF", () => {
    const source = { book: "subconscious_mind", metadata: {
        chapter: "Chapter 2: How Your Own Mind Works", page_start: 24, page_end: 24,
    } };
    assert.equal(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)), "The Power of Your Subconscious Mind");
    assert.match(
        AnswerFormat.formatHtml("The mind has two levels (Chapter 2, p.24).", [source]),
        /href="\/book\.pdf\?book=subconscious_mind#page=24".*The Power of Your Subconscious Mind/,
    );
});

test("links numbered web citations and rejects unsafe URLs", () => {
    const good = { kind: "web", index: 1, title: "Research", url: "https://example.org/study" };
    const bad = { kind: "web", index: 2, title: "Unsafe", url: "javascript:alert(1)" };
    const html = AnswerFormat.formatHtml("Habits vary [1]. Avoid [2].", [good, bad]);
    assert.match(html, /href="https:\/\/example\.org\/study"/);
    assert.match(html, /Avoid \[2\]/);
    assert.doesNotMatch(html, /javascript:/);
});

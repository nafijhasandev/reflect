const test = require("node:test");
const assert = require("node:assert/strict");
const StreamEvents = require("../web/static/stream_events.js");

test("parses streamed answer and source events", () => {
    assert.deepEqual(StreamEvents.parse('data: {"type":"chunk","content":"Hello"}'), {
        type: "chunk", content: "Hello",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"sources","sources":[]}'), {
        type: "sources", sources: [],
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"power_of_habit"}'), {
        type: "book_selected", book: "power_of_habit",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"power_of_now"}'), {
        type: "book_selected", book: "power_of_now",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"little_book_of_stoicism"}'), {
        type: "book_selected", book: "little_book_of_stoicism",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"five_second_rule"}'), {
        type: "book_selected", book: "five_second_rule",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"emotional_intelligence"}'), {
        type: "book_selected", book: "emotional_intelligence",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"art_of_thinking_clearly"}'), {
        type: "book_selected", book: "art_of_thinking_clearly",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"positive_thinking"}'), {
        type: "book_selected", book: "positive_thinking",
    });
    assert.deepEqual(StreamEvents.parse('data: {"type":"book_selected","book":"subconscious_mind"}'), {
        type: "book_selected", book: "subconscious_mind",
    });
    assert.equal(StreamEvents.parse(": heartbeat"), null);
    assert.equal(StreamEvents.parse("data: "), null);
});

test("rejects malformed or unexpected streamed events", () => {
    for (const line of [
        "data: {broken",
        "data: null",
        'data: {"type":"chunk","content":42}',
        'data: {"type":"sources","sources":{}}',
        'data: {"type":"unknown"}',
        'data: {"type":"book_selected","book":"unknown"}',
    ]) {
        assert.throws(() => StreamEvents.parse(line), /Invalid server event/);
    }
});

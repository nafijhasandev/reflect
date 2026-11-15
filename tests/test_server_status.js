const test = require("node:test");
const assert = require("node:assert/strict");
const ServerStatus = require("../web/static/server_status.js");

test("identifies a stale server when a newer book is selected", () => {
    assert.equal(ServerStatus.missingIndexMessage({ index_loaded: false, chunk_count: 0 },
        "little_book_of_stoicism"), "Restart Python server to load new books");
    assert.equal(ServerStatus.missingIndexMessage({ supported_books: ["atomic_habits"], chunk_count: 0 },
        "little_book_of_stoicism"), "Restart Python server to load new books");
});

test("separates missing indexes from rejected book IDs", () => {
    assert.equal(ServerStatus.missingIndexMessage({ supported_books: ["little_book_of_stoicism"],
        chunk_count: 0 }, "little_book_of_stoicism"), "Book index missing · run ingest");
    assert.match(ServerStatus.validationMessage({ detail: [{ loc: ["body", "book"] }] }),
        /older book settings/);
    assert.match(ServerStatus.validationMessage({ detail: [{ loc: ["body", "question"] }] }),
        /1000 characters/);
});

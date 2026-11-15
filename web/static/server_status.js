const ServerStatus = (() => {
    function missingIndexMessage(health, book) {
        const supported = Array.isArray(health?.supported_books) ? health.supported_books : null;
        if (!supported || (book !== "auto" && !supported.includes(book))) {
            return "Restart Python server to load new books";
        }
        if (!health.chunk_count) return "Book index missing · run ingest";
        return "Book index incomplete · retry shortly";
    }

    function validationMessage(payload) {
        const bookRejected = Array.isArray(payload?.detail) && payload.detail.some(
            issue => Array.isArray(issue.loc) && issue.loc.includes("book"));
        return bookRejected
            ? "The Python server is using older book settings. Restart it, then refresh this page."
            : "Please enter a question up to 1000 characters.";
    }

    return { missingIndexMessage, validationMessage };
})();

if (typeof module !== "undefined") module.exports = ServerStatus;

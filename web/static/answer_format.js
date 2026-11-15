const AnswerFormat = (() => {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

    function escapeHtml(text) {
        return String(text).replace(/[&<>"']/g, character => entities[character]);
    }

    function sourcePage(source) {
        const page = Number(source?.metadata?.page_start);
        return Number.isSafeInteger(page) && page > 0 ? page : null;
    }

    function sourceTopic(source) {
        const metadata = source?.metadata || {};
        return String(metadata.section || metadata.chapter || "").trim() || bookTitle(sourceBook(source));
    }

    function sourceBook(source) {
        return ["tiny_habits", "power_of_habit", "power_of_now", "little_book_of_stoicism", "five_second_rule", "emotional_intelligence", "art_of_thinking_clearly", "positive_thinking", "subconscious_mind"].includes(source?.book) ? source.book : "atomic_habits";
    }

    function webUrl(source) {
        if (source?.kind !== "web") return null;
        try {
            const url = new URL(String(source.url || ""));
            return ["http:", "https:"].includes(url.protocol) ? url.href : null;
        } catch {
            return null;
        }
    }

    function bookTitle(book) {
        return {
            auto: "All Books",
            atomic_habits: "Atomic Habits",
            tiny_habits: "Tiny Habits",
            power_of_habit: "The Power of Habit",
            power_of_now: "The Power of Now",
            little_book_of_stoicism: "The Little Book of Stoicism",
            five_second_rule: "The 5 Second Rule",
            emotional_intelligence: "Emotional Intelligence",
            art_of_thinking_clearly: "The Art of Thinking Clearly",
            positive_thinking: "The Power of Positive Thinking",
            subconscious_mind: "The Power of Your Subconscious Mind",
        }[book] || "Atomic Habits";
    }

    function sourceLink(source, page = sourcePage(source)) {
        if (!Number.isSafeInteger(page) || page < 1) return null;
        const topic = escapeHtml(sourceTopic(source));
        const book = sourceBook(source);
        const fullPdf = book === "atomic_habits" ? `/book.pdf#page=${page}` : `/book.pdf?book=${book}#page=${page}`;
        const bookAttribute = book === "atomic_habits" ? "" : ` data-pdf-book="${book}"`;
        const chunkId = String(source?.chunk_id || "");
        const hasChunk = /^[0-9a-f]{12}(?:_[1-9][0-9]*)?$/.test(chunkId);
        const chunkAttribute = hasChunk ? ` data-pdf-chunk="${chunkId}"` : "";
        const url = hasChunk ? `/source-page.pdf?book=${book}&amp;chunk_id=${chunkId}` : fullPdf;
        const start = sourcePage(source);
        const end = Number(source?.metadata?.page_end);
        const rangeAttribute = start !== null && Number.isSafeInteger(end) && end > start && end - start <= 4
            ? ` data-pdf-start="${start}" data-pdf-end="${end}"` : "";
        return `href="${url}" data-pdf-page="${page}"${bookAttribute}${chunkAttribute}${rangeAttribute} ` +
            `data-pdf-topic="${topic}" target="_blank" rel="noopener noreferrer"`;
    }

    function citationMatchesSource(source, chapter, page) {
        const metadata = source?.metadata || {};
        const chapterLabel = String(metadata.chapter || "").trim();
        const chapterMatch = /\bChapter\s+(\d+)\b/i.exec(chapterLabel);
        const chapterNumber = chapterMatch ? chapterMatch[1] : chapterLabel;
        const start = sourcePage(source);
        const end = Number(metadata.page_end);
        return chapterNumber === chapter && start !== null &&
            Number.isSafeInteger(end) && start <= page && page <= end;
    }

    function formatHtml(text, sources = []) {
        return String(text)
            .split(/\n\s*\n/)
            .filter(paragraph => paragraph.trim())
            .map(paragraph => {
                const escaped = escapeHtml(paragraph.trim());
                const headings = escaped.replace(/(^|\n)#{1,3}\s+([^\n]+)/g, "$1<strong>$2</strong>");
                const bold = headings.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
                const labels = bold.replace(/(^|\n)([^:\n]{3,140}:)(?=\s|$)/g, (match, start, label) =>
                    label.includes("<strong>") ? match : `${start}<strong>${label}</strong>`);
                const linked = labels.replace(/\(Chapter\s+(\d+),\s*p\.(\d+)\)/gi,
                    (citation, chapter, pageText) => {
                        const page = Number(pageText);
                        const source = (sources || []).find(source =>
                            citationMatchesSource(source, chapter, page));
                        if (!source) {
                            return citation;
                        }
                        return `<a class="citation-link" ${sourceLink(source, page)}>${citation} <span class="citation-book">${escapeHtml(bookTitle(sourceBook(source)))}</span></a>`;
                    });
                const pageLinked = linked.replace(/\(p\.(\d+)\)/gi, (citation, pageText) => {
                    const page = Number(pageText);
                    const source = (sources || []).find(source => {
                        const start = sourcePage(source);
                        const end = Number(source?.metadata?.page_end);
                        return start !== null && start <= page && Number.isSafeInteger(end) && page <= end;
                    });
                    return source ? `<a class="citation-link" ${sourceLink(source, page)}>${citation} <span class="citation-book">${escapeHtml(bookTitle(sourceBook(source)))}</span></a>` : citation;
                });
                const webLinked = pageLinked.replace(/\[(\d{1,2})\]/g, (citation, indexText) => {
                    const source = (sources || []).find(item => item?.kind === "web" &&
                        Number(item.index) === Number(indexText) && webUrl(item));
                    return source
                        ? `<a class="citation-link" href="${escapeHtml(webUrl(source))}" target="_blank" rel="noopener noreferrer">${citation}</a>`
                        : citation;
                });
                return `<p>${webLinked}</p>`;
            })
            .join("");
    }

    return { escapeHtml, formatHtml, sourcePage, sourceTopic, sourceLink, sourceBook, bookTitle, webUrl };
})();

if (typeof module !== "undefined") module.exports = AnswerFormat;

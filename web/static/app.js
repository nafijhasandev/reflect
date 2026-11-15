/**
 * Chat interface logic for reflect.
 *
 * Handles:
 * - Sending queries to the /api/query endpoint
 * - Parsing Server-Sent Events (SSE) for streaming responses
 * - Rendering messages and sources
 * - Auto-resizing the input textarea
 * - Health check on page load
 */

const chatContainer = document.getElementById("chatContainer");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const welcome = document.getElementById("welcome");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const app = document.querySelector(".app");
const chatList = document.getElementById("chatList");
const historyNotice = document.getElementById("historyNotice");
const sidebarToggle = document.getElementById("sidebarToggle");
const mainPanel = document.querySelector(".main-panel");
const settingsDialog = document.getElementById("settingsDialog");
const showSourcesToggle = document.getElementById("showSourcesToggle");
const settingsNotice = document.getElementById("settingsNotice");
const themeToggle = document.getElementById("themeToggle");
const themeNotice = document.getElementById("themeNotice");
const pdfPanel = document.getElementById("pdfPanel");
const pdfFrame = document.getElementById("pdfFrame");
const pdfOpen = document.getElementById("pdfOpen");
const pdfFull = document.getElementById("pdfFull");
const pdfTopic = document.getElementById("pdfTopic");
const pdfPage = document.getElementById("pdfPage");
const pdfBook = document.getElementById("pdfBook");
const bookSelect = document.getElementById("bookSelect");
const inputNote = document.getElementById("inputNote");
const welcomeCopy = document.getElementById("welcomeCopy");
const suggestions = [...document.querySelectorAll(".suggestion")];
const atomicSuggestions = suggestions.map(button => button.textContent);
const tinySuggestions = [
    "What is the Fogg Behavior Model?",
    "How do anchor moments work?",
    "Why does celebration help habits grow?",
    "How do I make a habit tiny?",
];
const powerSuggestions = [
    "What is the habit loop?",
    "What are keystone habits?",
    "How does Starbucks train willpower?",
    "How do social movements form?",
];
const nowSuggestions = [
    "What does Tolle mean by living in the Now?",
    "How can I observe the thinking mind?",
    "What is the pain-body?",
    "What does surrender mean in this book?",
];
const stoicismSuggestions = [
    "What is the Stoic dichotomy of control?",
    "How does negative visualization work?",
    "What is the Stoic morning routine?",
    "How should I respond to insults?",
];
const fiveSecondSuggestions = [
    "What is the 5 Second Rule?",
    "Why does counting backward help?",
    "How can I stop procrastinating?",
    "What is the Wake Up Challenge?",
];
const emotionalIntelligenceSuggestions = [
    "What is an emotional hijacking?",
    "How does self-awareness support emotional intelligence?",
    "What are the roots of empathy?",
    "How can schools teach emotional literacy?",
];
const thinkingClearlySuggestions = [
    "What is survivorship bias?",
    "How does the sunk cost fallacy affect decisions?",
    "What does Dobelli say about confirmation bias?",
    "Why can overconfidence lead to bad decisions?",
];
const positiveThinkingSuggestions = [
    "How can I build confidence in myself?",
    "How can I develop a peaceful mind?",
    "What is prayer power?",
    "How can I break the worry habit?",
];
const subconsciousMindSuggestions = [
    "How do the conscious and subconscious mind differ?",
    "How does suggestion affect the subconscious mind?",
    "What does Murphy say about visualization?",
    "How can the subconscious mind help with fear?",
];
const suggestionsByBook = {
    auto: ["What is the habit loop?", "What is survivorship bias?", "How can I break the worry habit?", "How does suggestion affect the subconscious mind?"],
    atomic_habits: atomicSuggestions,
    tiny_habits: tinySuggestions,
    power_of_habit: powerSuggestions,
    power_of_now: nowSuggestions,
    little_book_of_stoicism: stoicismSuggestions,
    five_second_rule: fiveSecondSuggestions,
    emotional_intelligence: emotionalIntelligenceSuggestions,
    art_of_thinking_clearly: thinkingClearlySuggestions,
    positive_thinking: positiveThinkingSuggestions,
    subconscious_mind: subconsciousMindSuggestions,
};
const escapeHtml = AnswerFormat.escapeHtml;

let isStreaming = false;
let chats = [];
try {
    chats = ChatHistory.load(localStorage);
} catch {
    historyNotice.textContent = "Saved chats could not be loaded in this browser.";
    historyNotice.hidden = false;
}
let activeChatId = null;
let settings = { showSources: true, theme: "dark" };
try {
    settings = ChatSettings.load(localStorage);
} catch {
    settingsNotice.textContent = "Saved settings could not be loaded in this browser.";
    settingsNotice.hidden = false;
}

function applySettings() {
    document.documentElement.dataset.theme = settings.theme;
    showSourcesToggle.checked = settings.showSources;
    const nextTheme = settings.theme === "dark" ? "light" : "dark";
    themeToggle.setAttribute("aria-label", `Switch to ${nextTheme} mode`);
    themeToggle.title = `Switch to ${nextTheme} mode`;
    app.classList.toggle("hide-sources", !settings.showSources);
}

function saveSettings() {
    try {
        ChatSettings.save(localStorage, settings);
        settingsNotice.hidden = true;
        themeNotice.hidden = true;
    } catch {
        settingsNotice.textContent = "Settings could not be saved in this browser.";
        settingsNotice.hidden = false;
        themeNotice.textContent = "Preference not saved";
        themeNotice.hidden = false;
    }
}

function saveHistory() {
    try {
        ChatHistory.save(localStorage, chats);
        historyNotice.hidden = true;
    } catch {
        historyNotice.textContent = "Chat history could not be saved in this browser.";
        historyNotice.hidden = false;
    }
}

function currentChat() {
    return chats.find(chat => chat.id === activeChatId);
}

function recordMessage(message) {
    currentChat().messages.push(message);
    saveHistory();
}

function renderChatList() {
    chatList.replaceChildren();
    for (const chat of [...chats].reverse()) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = chat.title;
        button.title = chat.title;
        button.className = chat.id === activeChatId ? "active" : "";
        button.setAttribute("aria-current", chat.id === activeChatId ? "page" : "false");
        button.addEventListener("click", () => {
            if (isStreaming) return;
            activeChatId = chat.id;
            renderConversation();
            renderChatList();
            closeSidebar();
        });
        chatList.appendChild(button);
    }
}

function renderConversation() {
    closePdf();
    chatContainer.replaceChildren();
    const chat = currentChat();
    if (chat) bookSelect.value = chat.book || "atomic_habits";
    const title = AnswerFormat.bookTitle(bookSelect.value);
    document.title = `reflect. · ${title}`;
    welcomeCopy.textContent = bookSelect.value === "auto"
        ? "Ask about habits, growth, or anything on your mind."
        : `Explore the ideas, examples, and chapters in ${title}.`;
    queryInput.placeholder = bookSelect.value === "auto" ? "Ask reflect. anything..." : `Ask about ${title}...`;
    queryInput.setAttribute("aria-label", bookSelect.value === "auto" ? "Ask reflect. a question" : `Ask a question about ${title}`);
    inputNote.textContent = bookSelect.value === "auto"
        ? "Books and web sources are used when helpful. Press Enter to send."
        : `Answers are based on ${title}. Press Enter to send.`;
    suggestions.forEach((button, index) => {
        button.textContent = (suggestionsByBook[bookSelect.value] || atomicSuggestions)[index];
    });
    checkHealth();
    mainPanel.classList.toggle("is-empty", !chat);
    if (!chat) {
        chatContainer.appendChild(welcome);
        return;
    }
    for (const message of chat.messages) {
        if (message.role === "user") {
            addUserMessage(message.text);
        } else {
            addAssistantMessage(message.text, message.sources || [], message.error);
        }
    }
    scrollToBottom();
}

function syncSidebarState() {
    const mobile = window.matchMedia("(max-width: 640px)").matches;
    const open = mobile ? app.classList.contains("sidebar-open") :
        !app.classList.contains("sidebar-collapsed");
    sidebarToggle.setAttribute("aria-expanded", String(open));
}

function closeSidebar() {
    app.classList.remove("sidebar-open");
    syncSidebarState();
}

function closePdf() {
    pdfPanel.hidden = true;
    app.classList.remove("pdf-open");
    pdfFrame.removeAttribute("src");
    pdfOpen.removeAttribute("href");
    pdfFull.removeAttribute("href");
}

function openPdf(page, topic, book = "atomic_habits", chunkId = "", rangeStart, rangeEnd) {
    if (!Number.isSafeInteger(page) || page < 1) return;
    const start = Number(rangeStart);
    const end = Number(rangeEnd);
    const first = Number.isSafeInteger(start) && start > 0 && start <= page &&
        Number.isSafeInteger(end) && page <= end && end - start <= 4 ? start : page;
    const last = first === start ? end : page;
    pdfPage.textContent = first === last ? `Page ${page}` : `Pages ${first}–${last}`;
    pdfBook.textContent = AnswerFormat.bookTitle(book);
    pdfTopic.textContent = topic || pdfBook.textContent;
    const hasChunk = /^[0-9a-f]{12}(?:_[1-9][0-9]*)?$/.test(chunkId);
    const fullPdf = book === "atomic_habits" ? `/book.pdf#page=${page}` : `/book.pdf?book=${book}#page=${page}`;
    const highlightedPdf = `/source-page.pdf?book=${book}&chunk_id=${chunkId}`;
    pdfFrame.src = hasChunk ? `${highlightedPdf}#page=1` : fullPdf;
    pdfOpen.href = hasChunk ? highlightedPdf : fullPdf;
    pdfOpen.textContent = hasChunk ? "Open highlighted PDF" : "Open source PDF";
    pdfFull.href = fullPdf;
    pdfFull.hidden = !hasChunk;
    pdfPanel.hidden = false;
    app.classList.add("pdf-open");
}

// ===== Health Check =====

async function checkHealth() {
    try {
        const suffix = bookSelect.value === "atomic_habits" ? "" : `?book=${bookSelect.value}`;
        const res = await fetch(`/api/health${suffix}`);
        if (!res.ok) throw new Error("Health check failed");
        const data = await res.json();

        if (data.llm_configured && data.index_loaded) {
            statusDot.className = "dot online";
            statusText.textContent = `Ready · ${data.chunk_count} passages`;
        } else if (data.index_loaded) {
            statusDot.className = "dot offline";
            statusText.textContent = "Add a Groq, OpenRouter, or Vercel API key to .env";
        } else {
            statusDot.className = "dot offline";
            statusText.textContent = ServerStatus.missingIndexMessage(data, bookSelect.value);
        }
    } catch {
        statusDot.className = "dot offline";
        statusText.textContent = bookSelect.value === "auto"
            ? "Restart the Python server to enable Auto"
            : "Server unreachable";
    }
}

// ===== Message Rendering =====

function addUserMessage(text) {
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = "message user";
    msg.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
    chatContainer.appendChild(msg);
    scrollToBottom();
}

function createAssistantMessage() {
    if (welcome) welcome.remove();

    const msg = document.createElement("div");
    msg.className = "message assistant";

    const avatar = document.createElement("span");
    avatar.className = "reflect-mark assistant-avatar";
    avatar.textContent = "r.";
    avatar.setAttribute("aria-hidden", "true");

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const assistantLabel = document.createElement("div");
    assistantLabel.className = "answer-assistant-label";
    assistantLabel.textContent = "reflect.";
    bubble.appendChild(assistantLabel);

    const loading = document.createElement("div");
    loading.className = "loading-dots";
    loading.innerHTML = "<span></span><span></span><span></span>";

    bubble.appendChild(loading);
    msg.appendChild(avatar);
    msg.appendChild(bubble);
    chatContainer.appendChild(msg);
    scrollToBottom();

    return { msg, bubble, loading };
}

function addAssistantMessage(text, sources, isError) {
    const { bubble, loading } = createAssistantMessage();
    loading.remove();
    const content = document.createElement("div");
    content.className = isError ? "error-msg" : "answer-content";
    content.innerHTML = AnswerFormat.formatHtml(text, sources);
    bubble.appendChild(content);
    renderSources(bubble, sources);
}

function renderSources(bubble, sources) {
    const validSources = (sources || []).filter(source => source && typeof source === "object");
    if (validSources.length === 0) return;

    const container = document.createElement("details");
    container.className = "sources";

    const header = document.createElement("summary");
    header.textContent = `${validSources.length} sources`;
    container.appendChild(header);

    validSources.forEach(source => {
        if (source.kind === "web") {
            const url = AnswerFormat.webUrl(source);
            if (!url) return;
            const item = document.createElement("div");
            item.className = "source-item";
            item.innerHTML = `<div class="source-meta"><strong>${escapeHtml(source.title || "Web source")}</strong> ` +
                `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open website</a></div>` +
                `<div class="source-text">${escapeHtml(source.text_preview || "")}</div>`;
            container.appendChild(item);
            return;
        }
        const meta = source.metadata && typeof source.metadata === "object" ? source.metadata : {};
        const chapter = String(meta.chapter || "").trim();
        const pageStart = meta.page_start || "?";
        const pageEnd = meta.page_end || "?";
        const preview = source.text_preview || "";
        const chapterLabel = /^\d+$/.test(chapter) ? `Chapter ${chapter}` : chapter;
        const pdfPage = AnswerFormat.sourcePage(source);
        const topic = String(meta.section || "").trim();
        const item = document.createElement("div");
        item.className = "source-item";
        item.innerHTML = `
            <div class="source-meta">
                <strong>${escapeHtml(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)))}</strong>
                ${chapterLabel ? `<strong>${escapeHtml(chapterLabel)}</strong>` : ""}
                ${topic && topic !== chapterLabel ? `<strong>${escapeHtml(topic)}</strong>` : ""}
                <span>Pages ${escapeHtml(pageStart)}-${escapeHtml(pageEnd)}</span>
                ${pdfPage ? `<a class="source-link" ${AnswerFormat.sourceLink(source)}>View page ${pdfPage} in ${escapeHtml(AnswerFormat.bookTitle(AnswerFormat.sourceBook(source)))}</a>` : ""}
            </div>
            <div class="source-text">${escapeHtml(preview)}...</div>
        `;
        container.appendChild(item);
    });

    bubble.appendChild(container);
}

// ===== Streaming Query =====

async function sendQuery(question) {
    if (isStreaming || !question.trim()) return;

    isStreaming = true;
    sendBtn.disabled = true;
    bookSelect.disabled = true;
    mainPanel.classList.remove("is-empty");
    if (!activeChatId) {
        const chat = ChatHistory.create(crypto.randomUUID(), question);
        chat.book = bookSelect.value;
        chats.push(chat);
        activeChatId = chat.id;
        renderChatList();
    }
    addUserMessage(question);
    recordMessage({ role: "user", text: question });

    const { bubble, loading } = createAssistantMessage();
    let resolvedBook = currentChat().book;

    let answerDiv = null;
    let sources = null;
    let answerText = "";
    let errorText = "";
    let requestError = "The response could not be completed. Please try again.";

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, book: currentChat().book || "atomic_habits" }),
        });

        if (!response.ok) {
            if (response.status === 422) {
                const validation = await response.json().catch(() => ({}));
                requestError = ServerStatus.validationMessage(validation);
            }
            throw new Error("Request failed");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                const event = StreamEvents.parse(line);
                if (!event) continue;

                if (event.type === "book_selected") {
                    resolvedBook = event.book;
                }

                if (event.type === "sources") {
                    sources = event.sources;
                }

                if (event.type === "chunk") {
                    if (!answerDiv) {
                        loading.remove();
                        answerDiv = document.createElement("div");
                        answerDiv.className = "answer-content";
                        bubble.appendChild(answerDiv);
                    }
                    answerDiv.textContent += event.content;
                    answerText += event.content;
                    scrollToBottom();
                }

                if (event.type === "error") {
                    loading.remove();
                    const errDiv = document.createElement("div");
                    errDiv.className = "error-msg";
                    errDiv.textContent = event.message;
                    bubble.appendChild(errDiv);
                    errorText = event.message;
                }

                if (event.type === "done") {
                    loading.remove();
                    if (typeof event.answer === "string" && event.answer) {
                        answerText = event.answer;
                    }
                    if (answerDiv) {
                        answerDiv.innerHTML = AnswerFormat.formatHtml(answerText, sources);
                    }
                    renderSources(bubble, sources);
                }
            }
        }
    } catch (error) {
        console.error("Chat response failed", error);
        loading.remove();
        const errDiv = document.createElement("div");
        errDiv.className = "error-msg";
        if (error.message === "Invalid server event") {
            requestError = "Browser files are out of date. Refresh the page with Ctrl+F5 and try again.";
        }
        errDiv.textContent = requestError;
        bubble.appendChild(errDiv);
        errorText = requestError;
    } finally {
        if (!answerText && !errorText) {
            errorText = "The response ended unexpectedly. Please try again.";
            loading.remove();
            const errDiv = document.createElement("div");
            errDiv.className = "error-msg";
            errDiv.textContent = errorText;
            bubble.appendChild(errDiv);
        }
        recordMessage({
            role: "assistant",
            text: [answerText, errorText].filter(Boolean).join("\n\n"),
            sources: answerText ? sources || [] : [],
            book: resolvedBook,
            error: !answerText,
        });
        isStreaming = false;
        sendBtn.disabled = false;
        bookSelect.disabled = false;
        queryInput.focus();
        scrollToBottom();
    }
}

// ===== Event Handlers =====

function handleSubmit(e) {
    e.preventDefault();
    const question = queryInput.value.trim();
    if (question) {
        queryInput.value = "";
        queryInput.style.height = "auto";
        sendQuery(question);
    }
}

function askSuggestion(btn) {
    sendQuery(btn.textContent);
}

document.getElementById("newChatBtn").addEventListener("click", () => {
    if (isStreaming) return;
    activeChatId = null;
    renderConversation();
    renderChatList();
    closeSidebar();
    queryInput.focus();
});

bookSelect.addEventListener("change", () => {
    if (isStreaming) return;
    activeChatId = null;
    renderConversation();
    renderChatList();
});

chatContainer.addEventListener("click", event => {
    const link = event.target.closest("a[data-pdf-page]");
    if (!link || !chatContainer.contains(link)) return;
    event.preventDefault();
    openPdf(Number(link.dataset.pdfPage), link.dataset.pdfTopic,
        link.dataset.pdfBook, link.dataset.pdfChunk,
        link.dataset.pdfStart, link.dataset.pdfEnd);
});
document.getElementById("closePdfBtn").addEventListener("click", closePdf);

sidebarToggle.addEventListener("click", () => {
    if (window.matchMedia("(max-width: 640px)").matches) {
        app.classList.toggle("sidebar-open");
    } else {
        app.classList.toggle("sidebar-collapsed");
    }
    syncSidebarState();
});

document.getElementById("sidebarBackdrop").addEventListener("click", closeSidebar);
window.addEventListener("resize", syncSidebarState);

document.getElementById("settingsBtn").addEventListener("click", () => {
    closeSidebar();
    settingsDialog.showModal();
});
document.getElementById("closeSettingsBtn").addEventListener("click", () => {
    settingsDialog.close();
});
showSourcesToggle.addEventListener("change", () => {
    settings = { ...settings, showSources: showSourcesToggle.checked };
    applySettings();
    saveSettings();
});
themeToggle.addEventListener("click", () => {
    settings = { ...settings, theme: settings.theme === "dark" ? "light" : "dark" };
    applySettings();
    saveSettings();
});

// Auto-resize textarea
queryInput.addEventListener("input", () => {
    queryInput.style.height = "auto";
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
});

// Enter to send, Shift+Enter for newline
queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
    }
});

// ===== Utilities =====

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ===== Init =====
renderChatList();
renderConversation();
applySettings();
syncSidebarState();

# How reflect. Works

reflect. answers questions using passages from the selected local PDF. The books, search indexes, embedding model, and reranker run locally. Hosted providers generate the answer. See [SETUP.md](SETUP.md) for commands to install and run it.

## Ingestion

Run `python main.py ingest` once after setup. `ingestion/pipeline.py` coordinates these steps:

1. `ingestion/pdf_processor.py` extracts PDF text blocks and detects chapter and topic headings, including headings in the middle of a page.
2. `ingestion/chunker.py` assigns each paragraph to its most recent topic. It never mixes different topics in one chunk. Long topics become smaller overlapping chunks with the same topic label. The target is 800 characters with 100 characters of overlap so most passages fit the embedding model's input window. Sentence boundaries stay intact, including unusually long sentences.
   The supplied Bookey Tiny Habits PDF uses a dedicated parser: it indexes each substantive summary heading with its body, splits dense summaries and quote groups into focused passages, preserves each question with its full answer, tracks chapter changes within a page, and excludes the unmarked true/false quiz and promotional pages. A different Tiny Habits PDF falls back to the general topic chunker.
   The supplied Power of Now PDF uses an edition-specific cleanup step to remove duplicated heading words and assign the correct ten chapter labels. Its introduction and chapters retain original PDF page numbers.
   The supplied Little Book of Stoicism PDF uses a dedicated parser to preserve eight chapter labels and 55 numbered practices. It excludes cover, part title pages, acknowledgments, bibliography, and promotion while retaining PDF page numbers.
   The supplied 5 Second Rule PDF uses a dedicated parser to preserve 17 chapters, three introductions between parts, and its closing section. It repairs large drop caps that split the first word of a chapter and excludes contents, part title pages, and the final promotional page.
   The supplied Emotional Intelligence PDF uses its table of contents page numbers to preserve the introduction, 16 chapters, and six appendices. It excludes contents, part title pages, notes, and publisher matter while retaining original PDF page numbers.
   The supplied Art of Thinking Clearly PDF uses its bookmarks to preserve 99 named thinking-error chapters, plus the introduction and epilogue. It joins each chapter heading and bias name to its first paragraph so search does not index a title alone.
   The supplied Power of Positive Thinking PDF uses a dedicated parser for its 17 chapters. It splits shared pages at mid-page chapter headings and removes repeated running headers and page labels before chunking.
   The supplied Power of Your Subconscious Mind PDF uses its bookmarks for ten opening sections and 20 numbered chapters. It removes repeated promotional footers and closing advertising before chunking.
3. `core/embeddings.py` converts each chunk into a normalized vector using `sentence-transformers/all-MiniLM-L6-v2`, in batches of 32.
4. `core/vector_store.py` writes vectors, text, and metadata to a cosine-distance ChromaDB collection. `core/bm25_index.py` builds a keyword index from the same chunks.

The indexes are stored under `data/`. Atomic Habits keeps `data/chunks.json` and `data/bm25_index.pkl`; each other book uses `data/<book>_chunks.json` and `data/<book>_bm25_index.pkl`. The chunk JSON files are inspection copies and are not read during search. Each book has its own ChromaDB collection. Use `python main.py ingest --force --book power_of_now` after changing that PDF or the chunking rules; omit `--book` to rebuild Atomic Habits.

## Answering a question

Standalone greetings and courtesies receive a brief reply from reflect. asking what the user would like to know. Substantive questions receive a direct answer even when the books do not cover them.

Before scope checks and search, clear spelling mistakes in common book terms are repaired conservatively. The original message remains visible in the chat; ambiguous words are left unchanged. Auto book selection and the selected book's retrieval use the repaired wording.

In the web UI's **Auto · best matching book** mode, `core/book_summaries.py` supplies a short profile of each indexed PDF. `core/book_router.py` retrieves the top passages from every available book and scores the summaries and passages with the same local cross-encoder. The summaries resolve close book choices, while a book must have an actual retrieved passage to be selected. The chosen book's normal RAG pipeline then builds the answer from its chunks and supplies its PDF citations. Clearly unrelated questions skip book selection and use general answering. The summaries are routing aids, never answer context. Review the summaries if a PDF is replaced with a substantially different book or edition.

`core/query_engine.py` handles CLI and web questions:

1. A rule-based scope check sends clearly unrelated questions to general answering without searching the book indexes. `core/web_search.py` optionally retrieves a few public search snippets for these questions; no additional API key is needed. Set `WEB_SEARCH_ENABLED=false` to disable this search. When search is unavailable, the model can answer from general knowledge while avoiding invented citations and precise unsupported figures.
2. The query classifier selects a factual, analytical, comparison, or summary prompt. By default, factual questions use three passages, analytical and comparison questions use five, and summaries use eight. Comparison questions search each named subject separately.
3. If a provider key is configured, query expansion suggests alternate wording. An expansion failure falls back to the original question.
4. `core/retriever.py` searches ChromaDB and BM25. Reciprocal Rank Fusion merges each search's ranked results. Results from expanded queries are scored together and capped at 15 unique candidates before reranking.
5. `core/reranker.py` scores the candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2` and keeps the highest scoring chunks.
6. `core/context_builder.py` orders the chosen passages by page, removes near duplicates, adds chapter, page, and topic labels, and limits context length.
7. `core/llm_client.py` sends the question and context to Groq, then OpenRouter and Vercel AI Gateway if earlier providers fail. Streaming switches providers only before any answer text has been shown, avoiding duplicate partial answers. For general questions, the prompt asks for a direct natural answer and can include both book passages and public web snippets. Search is also used for factual questions such as “how long” when a book passage alone may not give a usable answer. `core/citations.py` validates book chapter and page citations; general answers do not gain an unrelated book citation automatically. Web snippets carry numbered links, and the source panel displays them alongside any book passages actually cited. The answer and source metadata are returned to the CLI or streamed to the browser.

The web API is `POST /api/query`. It sends Server-Sent Events in this order: `metadata` with query type, zero or more answer `chunk` events, `sources`, then `done` with the final formatted answer; failures use an `error` event. `GET /api/health` reports index status and whether a provider key is configured. The browser streams draft answer text, then replaces it with the citation-checked answer when `done` arrives. The source panel lists the retrieved passages.

Source locations come from PDF metadata. Citation validation checks locations, not whether every claim is supported by its cited passage. Web results are short third-party snippets, not verified full pages; follow their links before relying on an important claim. If every configured provider fails, the CLI query can still return retrieved sources.

Clicking a citation opens the original PDF source pages in a native PDF viewer with yellow highlight annotations. The strongest matching page appears first, followed by the other pages in that source chunk. For Tiny Habits question-and-answer chunks, only the answer lines are marked. The **Open highlighted PDF** link opens the same annotated source PDF in a new tab; **Original book** opens the unmodified full book. This shows the supporting passage, since a generated answer may paraphrase the book rather than repeat its exact words.

## Performance and tuning

`config.py` sets chunk size, retrieval counts, context limit, and model names. `QueryEngine.query()` records time spent in classification, expansion, retrieval, reranking, context building, and generation. The CLI prints the main timings.

On November 5, 2026, an offline local probe used the 576-chunk index, a stored ChromaDB embedding, and 30 warmed runs of a five-chunk context. Median context assembly fell from 2.51 ms to 1.36 ms after reusing each chunk's text bigrams during duplicate detection. ChromaDB search measured 2.65 ms before and 4.16 ms after in separate runs, so those figures should not be treated as a change caused by this patch. BM25 and rank fusion were below 1 ms in both runs.

The quality tests use fixed ranked results to verify fusion behavior, a small indexed corpus to check BM25 scoring, and a ten-page PDF excerpt to check matching ChromaDB and BM25 chunk IDs. A manual full-book probe found the expected chapter within the top three passages for habit stacking, the two-minute rule, and the four laws of behavior change. A broader retrieval quality evaluation still needs more labeled book questions and expected passages.

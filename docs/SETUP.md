# Set Up reflect.

These commands use Windows PowerShell from the project folder. Python 3.11 or newer and the book PDF are required. Answer generation needs a Groq, OpenRouter, or Vercel AI Gateway API key. The commands below use Python 3.12.

## Install

```powershell
cd path\to\RAGSystem
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The first ingest and first server start download the embedding and reranker models from Hugging Face into `data/model_cache`. Their names are in `config.py`.

## Configure hosted models

Open the local `.env` file in the project folder and paste your keys after the equals signs:

```text
GROQ_API_KEY=
OPENROUTER_API_KEY=
VERCEL_API_KEY=
```

The app uses Groq first, OpenRouter second, and Vercel AI Gateway third. It skips providers without a key and tries the next provider if a request fails or hits a rate limit. The defaults are `openai/gpt-oss-120b` on Groq, `openrouter/free` on OpenRouter, and `nvidia/nemotron-3.5-lightning-free` on Vercel. OpenRouter's `openrouter/auto` can select paid models, so the default uses its free router. To change a model, add `GROQ_MODEL=`, `OPENROUTER_MODEL=`, or `VERCEL_AI_MODEL=` to `.env` with the desired model ID. Restart the server after editing `.env`. The file is excluded by `.gitignore` and must not be shared.

Vercel's free Nemotron provider may retain prompts and responses for model improvement. Each model request includes the question and retrieved book passages.

## Build the indexes

Place legally obtained copies of the books you want to use in the project folder: `Atomic Habits by James Clear.pdf.pdf`, `tiny-habits.pdf`, the 386-page `Charles-Duhigg.The-Power-of-Habit.pdf`, the 220-page `The Power of Now.pdf`, the 229-page `[Jonas_Salzgeber]_The_Little_Book_of_Stoicism__Tim(z-lib.org).pdf`, the 252-page `[Mel_Robbins]_The_5_Second_Rule__Transform_your_Li(z-lib.org).pdf`, the 312-page `Emotional Intelligence Why it Can Matter More Than IQ by Daniel Goleman.pdf`, the 225-page `Rolf Dobelli - The Art of Thinking Clearly _ Better thinking, Better decision-Sceptre (Hodder _ Stoughton Ltd) (2013).pdf`, the 128-page `The Power of Positive Thinking .pdf`, and/or the 171-page `The Power of Your Subconscious Mind.pdf`. You can change their paths in `config.py`. Book PDFs are excluded from GitHub. Run the relevant command for each available PDF:

```powershell
.\venv\Scripts\python.exe main.py ingest
.\venv\Scripts\python.exe main.py ingest --book tiny_habits
.\venv\Scripts\python.exe main.py ingest --book power_of_habit
.\venv\Scripts\python.exe main.py ingest --book power_of_now
.\venv\Scripts\python.exe main.py ingest --book little_book_of_stoicism
.\venv\Scripts\python.exe main.py ingest --book five_second_rule
.\venv\Scripts\python.exe main.py ingest --book emotional_intelligence
.\venv\Scripts\python.exe main.py ingest --book art_of_thinking_clearly
.\venv\Scripts\python.exe main.py ingest --book positive_thinking
.\venv\Scripts\python.exe main.py ingest --book subconscious_mind
```

This creates separate ChromaDB collections and BM25 files under `data/`. Ingestion skips a populated collection. The Power of Habit ingestion keeps the prologue, nine chapters, and appendix, with chapter sections as topic labels. Contents, part title pages, acknowledgments, notes, and index pages are excluded from search.
The Power of Now ingestion keeps the introduction and ten chapters, cleans repeated PDF heading words, and preserves PDF page numbers for citations.
The Little Book of Stoicism ingestion keeps the introduction, eight chapters, and 55 numbered practices while excluding front matter and end matter.
The 5 Second Rule ingestion keeps its 17 chapters, three short introductions between parts, and closing section. It fixes drop caps in the extracted text and preserves original PDF page numbers.
Emotional Intelligence ingestion keeps its introduction, 16 chapters, and six appendices while excluding contents, part dividers, notes, and publisher pages. Citations use original PDF page numbers.
The Art of Thinking Clearly ingestion uses its PDF bookmarks to keep the introduction, 99 named thinking-error chapters, and epilogue. It excludes contents and publisher pages while preserving original PDF page numbers.
The Power of Positive Thinking ingestion keeps its introduction and 17 chapters, splits pages where a new chapter starts midway through, and removes repeated headers and page labels. Citations use original PDF page numbers.
The Power of Your Subconscious Mind ingestion keeps ten opening sections and 20 chapters, removes repeated promotional footers and the closing promotion, and preserves original PDF page numbers.

To rebuild a book after changing its PDF or the chunk settings, run:

```powershell
.\venv\Scripts\python.exe main.py ingest --force
.\venv\Scripts\python.exe main.py ingest --force --book tiny_habits
.\venv\Scripts\python.exe main.py ingest --force --book power_of_habit
.\venv\Scripts\python.exe main.py ingest --force --book power_of_now
.\venv\Scripts\python.exe main.py ingest --force --book little_book_of_stoicism
.\venv\Scripts\python.exe main.py ingest --force --book five_second_rule
.\venv\Scripts\python.exe main.py ingest --force --book emotional_intelligence
.\venv\Scripts\python.exe main.py ingest --force --book art_of_thinking_clearly
.\venv\Scripts\python.exe main.py ingest --force --book positive_thinking
.\venv\Scripts\python.exe main.py ingest --force --book subconscious_mind
```

## Ask a question

```powershell
.\venv\Scripts\python.exe main.py query "What is habit stacking?"
.\venv\Scripts\python.exe main.py query --book tiny_habits "What is an anchor moment?"
.\venv\Scripts\python.exe main.py query --book power_of_habit "What is the habit loop?"
.\venv\Scripts\python.exe main.py query --book power_of_now "What is the pain-body?"
.\venv\Scripts\python.exe main.py query --book little_book_of_stoicism "What is negative visualization?"
.\venv\Scripts\python.exe main.py query --book five_second_rule "Why does counting backward help?"
.\venv\Scripts\python.exe main.py query --book emotional_intelligence "What is an emotional hijacking?"
.\venv\Scripts\python.exe main.py query --book art_of_thinking_clearly "What is survivorship bias?"
.\venv\Scripts\python.exe main.py query --book positive_thinking "How can I break the worry habit?"
.\venv\Scripts\python.exe main.py query --book subconscious_mind "How do the conscious and subconscious mind differ?"
.\venv\Scripts\python.exe main.py serve
```

Open `http://localhost:8000` in a browser. The server stays active in that terminal until you press Ctrl+C. The default **Auto · best matching book** option uses short book summaries and compares actual passages from all indexed books when the question is book-related. Other questions receive a general answer; a small public web search supplies linked snippets when available. Web search needs no extra key and can be disabled with `WEB_SEARCH_ENABLED=false` in `.env`. You can also select one book to focus its search. `http://localhost:8000/api/health` reports whether the index is loaded and at least one provider key is configured. The CLI prints the answer, source passages, and pipeline timings. The web page streams the answer and shows sources in its source panel. The local server reloads when Python files change and discovers new indexes after ingestion; restart it after editing `.env`, and use Ctrl+F5 after updating browser files.

## Tests and lint

```powershell
.\venv\Scripts\python.exe -m pytest tests -q
.\venv\Scripts\python.exe -m pip install ruff
.\venv\Scripts\ruff.exe check core ingestion web tests main.py config.py
$jsTests = (Get-ChildItem .\tests -Filter '*.js').FullName
node --test $jsTests
```

The Python tests mock hosted model requests and use temporary local PDF and index data. They do not need API keys or a model download. The JavaScript tests need Node.js. Install Ruff once if it is not already in the virtual environment.

## Common problems

- **Model download fails:** Restore network access to Hugging Face, then retry. An offline machine needs the model files cached from a prior successful run.
- **No model provider configured:** Put at least one API key in `.env`, then restart the server.
- **All providers fail:** Check each account's key, rate limit, and model availability. The app tries only providers with configured keys.
- **No ingested data:** Run the ingest command before starting the web server.
- **PDF not found:** Check the filename and `PDF_PATH` in `config.py`.
- **Wrong or stale search results:** Rebuild both indexes with `ingest --force` after confirming the PDF and chunk settings.
- **Old L2 vector index:** Rebuild with `ingest --force` to create a cosine collection and normalized vectors.
- **Port 8000 already in use:** Stop the other process using that port, or change `WEB_PORT` in `config.py`.

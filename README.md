# News Fetcher & Semantic Search (LangChain + Chroma)

AI-powered news aggregation with full-text extraction, LLM analysis, and semantic search.
Fetch from multiple RSS sources, extract full article text, summarize/tag with OpenAI via **LangChain**, store embeddings in **ChromaDB**, and query from an interactive CLI.

* **Python 3.11**
* **LangChain** for LLM orchestration (summaries, Q\&A)
* **ChromaDB** for a local, persistent vector store (no external DB required)
* **feedparser + trafilatura** for robust feed parsing & article text extraction
* **Rich / tqdm** for friendly progress & stats
* **Pytest** with helpful test header/summary

---

## Table of Contents

* [Architecture](#architecture)
* [Project Layout](#project-layout)
* [Requirements](#requirements)
* [Setup (Local)](#setup-local)
* [Environment (.env)](#environment-env)
* [Quick Start](#quick-start)
* [Usage](#usage)

  * [Fetching (with per-source text stats)](#fetching-with-per-source-text-stats)
  * [Analysis (LLM summaries/tags/sentiment)](#analysis-llm-summariestagssentiment)
  * [Interactive Search (Auto-build + RAG)](#interactive-search-auto-build--rag)
* [Testing](#testing)
* [Docker (Build & Run)](#docker-build--run)
* [Troubleshooting](#troubleshooting)
* [Notes & Tips](#notes--tips)
* [License](#license)

---

## Architecture

1. **Fetch** – `news_fetcher.py`

   * Read RSS feeds, normalize items (title/desc/link/date)
   * Try `<content:encoded>`; if missing, fetch the article HTML and **extract full text** via `trafilatura`
   * Write JSONL to `news_data/`
   * Print **per-source text stats** (avg/max chars & words)

2. **Analyze** – `analysis.py` (via **LangChain**)

   * For each article: generate **summary**, **topics**, and **sentiment** using your OpenAI model
   * **Token-safe**: if an article is short, do a single-shot summary. If it’s long, **chunk** it into overlapping parts, **summarize each chunk**, then **combine** into one final JSON (**summary**, **topics**, **sentiment**).
   * Progress bar, periodic throughput logs, and a final summary
   * Write JSONL to `analysis_results/`

3. **Embed & Index** – `vector_db.py` (OpenAI embeddings → **ChromaDB**)

   * Build a **persistent** local collection under `chroma_db/`
   * Metadata sanitized for Chroma (lists → comma-separated strings, telemetry disabled)

4. **Query** – `search_interface.py`

   * Interactive CLI with `/search`, `/ask` (RAG over retrieved context), `/stats`, `/rebuild`
   * **Auto-builds** vectors on first run if the collection is empty

---

## Project Layout

```
news_fetcher_ds/
├─ news_fetcher.py          # Stage 1: fetch feeds → news_data/, full-text extraction, per-source stats
├─ analysis.py              # Stage 2: LLM summaries/tags/sentiment → analysis_results/
├─ vector_db.py             # Stage 3: embeddings + ChromaDB (persistent in chroma_db/)
├─ search_interface.py      # Stage 4: interactive CLI (auto-build; /search, /ask, /stats, /rebuild)
├─ tests/
│  ├─ test_metadata.py
│  ├─ test_stats.py
│  └─ test_utils.py
├─ tests/conftest.py        # import shim + nice pytest header/summary
├─ pytest.ini               # informative defaults (-vv, durations)
├─ requirements.txt         # all dependencies
├─ .env.example             # sample configuration (copy to .env and edit)
└─ README.md                # this file
```

---

## Requirements

* **Python** 3.11
* **OpenAI API key** (for analysis & embeddings)
* macOS / Linux / Windows

---

## Setup (Local)

```bash
# 1) Clone
git clone https://github.com/pmazanik/news_fetcher_ds.git
cd news_fetcher_ds

# 2) Create & activate venv (optional but recommended)
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

# 3) Install deps
pip install -U pip
pip install -r requirements.txt

# 4) Configure environment
cp .env.example .env
# open .env and set OPENAI_API_KEY and FEED_URLS (see below)
```

---

## Environment (.env)

Here’s a **complete** example you can paste into `.env`. `FEED_URLS` is multi-line for clarity; entries are `Name|URL,rss` separated by semicolons/newlines.

```env
# ========= OpenAI =========
OPENAI_API_KEY=sk-REPLACE_ME

# Models
MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# ========= IO Paths =========
OUTPUT_DIR=news_data
ANALYSIS_DIR=analysis_results

# ========= Vector DB (Chroma) =========
CHROMA_DIR=chroma_db
CHROMA_COLLECTION=news_articles
# Auto-build index on first launch of search_interface.py if empty
AUTO_BUILD=true

# ========= Fetcher runtime =========
USER_AGENT=news-fetcher/1.0 (+https://example.local)
REQUEST_DELAY=0.3
MAX_ARTICLES_PER_SOURCE=50

# Full-text extraction settings
CONTENT_FETCH=true
CONTENT_CONCURRENCY=5
CONTENT_TIMEOUT=20

# ========= Analysis runtime =========
ANALYSIS_LOG_EVERY=50
ANALYSIS_MAX_ITEMS=0   # 0 = process all

# Token-safe chunking controls (character-based)
# If article length <= ANALYSIS_SINGLE_SHOT_CHARS -> single-shot
# Otherwise -> chunk into ANALYSIS_CHUNK_CHARS with ANALYSIS_CHUNK_OVERLAP, then combine
ANALYSIS_SINGLE_SHOT_CHARS=12000
ANALYSIS_CHUNK_CHARS=6000
ANALYSIS_CHUNK_OVERLAP=500
ANALYSIS_MAX_CHUNKS=10

# ========= News sources =========
# Use ; or newlines between entries. Each entry: Name|URL,rss
# Keep the opening and closing quote, and avoid trailing separators.
FEED_URLS="BBC-World|https://feeds.bbci.co.uk/news/world/rss.xml,rss;
Guardian-World|https://www.theguardian.com/world/rss,rss;
AlJazeera|https://www.aljazeera.com/xml/rss/all.xml,rss;
DW-Top|https://rss.dw.com/rdf/rss-en-top,rss"
```

> Tip: You can omit `FEED_URLS` to use defaults, but the above is recommended.
> Some sources (e.g., AP, NPR) may not provide stable public RSS; if a source returns 0 items, swap it out.

---

## Quick Start

```bash
# 1) Fetch (RSS + full-text extraction)
python news_fetcher.py

# 2) Analyze (LLM summaries, topics, sentiment)
python analysis.py

# 3) Interactive search (auto-builds vectors if empty)
python search_interface.py
```

In the CLI, try:

```
/search central bank inflation
/ask "What did BBC report today?"
/stats
/rebuild
/help
```

---

## Usage

### Fetching (with per-source text stats)

```bash
python news_fetcher.py
```

* Parses RSS via **feedparser**; if the feed lacks full text, fetches HTML and extracts with **trafilatura**.
* Writes JSONL files into `news_data/` like `news_YYYYMMDD_HHMMSS.jsonl`.
* Prints a **Per-source Text Stats** table:

```
Per-source Text Stats
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Source     ┃ Count ┃ Avg chars┃ Avg words┃ Max chars┃ Max words┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ BBC-World  │   44  │  5700.34 │   920.55 │    19876 │     3291 │
│ Guardian…  │   45  │  6201.77 │  1001.23 │    24310 │     4152 │
│ AlJazeera  │   25  │  5402.10 │   870.02 │    20144 │     3420 │
│ DW-Top     │   50  │  4980.05 │   801.41 │    18990 │     3108 │
└────────────┴───────┴──────────┴──────────┴──────────┴──────────┘
```

> If a source fails DNS or returns 0 items, it’s logged and the run **continues**.

### Analysis (LLM summaries/tags/sentiment)

```bash
python analysis.py
```

* Uses **LangChain** (`ChatOpenAI`) for enrichment.
* **Token-safe behavior**:

  * If the article text is **short** (≤ `ANALYSIS_SINGLE_SHOT_CHARS`), the model gets the whole text in **one call** and returns JSON.
  * If the article text is **long**, the script:

    1. **Chunks** the text into overlapping pieces (`ANALYSIS_CHUNK_CHARS`, overlap `ANALYSIS_CHUNK_OVERLAP`),
    2. **Summarizes** each chunk (2–3 sentences),
    3. **Combines** those mini-summaries into **one** JSON result: `summary`, `topics[]`, `sentiment`.
* Shows a progress bar + periodic throughput, and a final summary.
* Writes to `analysis_results/analysis_*.jsonl`.

* **Tuning common cases**

* Use a smaller-context model → **lower** `ANALYSIS_SINGLE_SHOT_CHARS` and `ANALYSIS_CHUNK_CHARS`.
* Extremely long articles → you can **raise** `ANALYSIS_MAX_CHUNKS` slightly (e.g., 12), but remember the combine step also needs room.


### Interactive Search (Auto-build + RAG)

```bash
python search_interface.py
```

* If the Chroma collection is empty, it **auto-builds** from the latest `analysis_results/*.jsonl`.
* `/search <text>` returns top-k semantic matches.
* `/ask "your question"` performs a simple **RAG**: retrieve context → answer with LangChain ChatOpenAI.
* `/stats` shows Chroma collection + points; `/rebuild` forces a re-index from latest analysis.

---

## Testing

We ship a lightweight test suite (no network calls):

```bash
pytest
# or, with defaults: -vv -ra --durations=5 (from pytest.ini)
```

What you’ll see:

* A header with Python & key package versions, model/env toggles, and FEED\_URLS count
* Verbose test names and slowest tests
* A compact end-of-run summary (totals, elapsed)

Tests include:

* `tests/test_utils.py` – URL canonicalization & hashing
* `tests/test_stats.py` – per-source text metrics
* `tests/test_metadata.py` – Chroma metadata sanitization (lists → string, None drop)

> We preload `news_fetcher.py` & `vector_db.py` for import reliability in `tests/conftest.py`, and disable Chroma telemetry in tests.

---

## Docker (Build & Run)

**Dockerfile** (save as `Dockerfile` at repo root):

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY . .
# Non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default: open the interactive search
CMD ["python", "search_interface.py"]
```

**.dockerignore** (recommended):

```
.venv
__pycache__
*.pyc
.env
news_data/
analysis_results/
chroma_db/
```

**Build:**

```bash
docker build -t news-fetcher .
```

**Create host folders once:**

```bash
mkdir -p news_data analysis_results chroma_db
```

**Run fetch:**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/chroma_db:/app/chroma_db" \
  news-fetcher \
  python news_fetcher.py
```

**Run analysis:**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/chroma_db:/app/chroma_db" \
  news-fetcher \
  python analysis.py
```

**Interactive search:**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/chroma_db:/app/chroma_db" \
  news-fetcher
# then type /search, /ask, /stats, /rebuild
```

> You can also override single envs without `--env-file`, e.g. `-e OPENAI_API_KEY=...`.

---

## Troubleshooting

* **DNS / connect errors** during fetch

  * Verify your network/proxy; the fetcher honors `HTTP(S)_PROXY` via `httpx.AsyncClient(trust_env=True)`.
  * If one source fails, others still proceed; swap or remove problematic feeds in `.env`.

* **No items for a source**

  * Some outlets don’t maintain public RSS or block bots. Replace with alternatives (BBC, Guardian, Al Jazeera, DW, etc.).

* **Telemetry messages from Chroma**

  * We hard-disable Chroma/PostHog telemetry in `vector_db.py` (envs + logger) so the CLI stays clean.

* **Changed embedding model**

  * If you switch `EMBEDDING_MODEL`, clear or change `CHROMA_COLLECTION` and rebuild (`/rebuild`).

* **Costs / rate limits**

  * Limit items via `MAX_ARTICLES_PER_SOURCE` and run analysis in batches (also `ANALYSIS_MAX_ITEMS`).

---

## Notes & Tips

* The fetcher prints **per-source text stats** (avg/max chars & words) so you can quickly see which feeds yield fuller articles.
* `analysis.py` shows a progress bar with periodic throughput; tweak `ANALYSIS_LOG_EVERY`.
* Smaller-context models → lower `ANALYSIS_SINGLE_SHOT_CHARS` and `ANALYSIS_CHUNK_CHARS`.
* Keep overlap \~10–20% of chunk size.
* `ANALYSIS_MAX_CHUNKS` caps the number of chunk summaries sent to the combine step.
* `search_interface.py` **auto-builds** on first run if needed; use `/rebuild` after new analyses.

---

## License

**MIT** — see `LICENSE` (or the repo’s license section).


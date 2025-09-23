# News Fetcher & Semantic Search

AI-powered news aggregation + LLM analysis + semantic search.
The pipeline fetches articles from multiple sources, summarizes/tags them with OpenAI, builds a lightweight on-disk vector index, and lets you query in natural language from an interactive CLI.

* Python 3.9+ (3.11 recommended)
* Runs locally or in Docker
* Zero infra: vectors + metadata stored as JSON on disk

---

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Repository Layout](#repository-layout)
* [Requirements](#requirements)
* [Setup (Local)](#setup-local)
* [Quick Start](#quick-start)
* [Usage](#usage)
* [Configuration](#configuration)
* [Data & Folders](#data--folders)
* [Testing](#testing)
* [Docker (Build & Run)](#docker-build--run)
* [Troubleshooting](#troubleshooting)
* [Roadmap](#roadmap)
* [License](#license)

---

## Overview

**What it does**

* Fetches news from several curated sources.
* Uses an OpenAI model to produce **summary**, **topics**, **sentiment** (and other light analysis).
* Creates **embeddings** for each article and stores everything in a single JSON “vector DB”.
* Provides an **interactive CLI** for semantic `/search` and Q\&A `/ask` over the corpus.

**Who it’s for**

* Developers/researchers prototyping a news intelligence/search workflow.
* Teams that want a simple, portable RAG-style baseline without maintaining a DB service.

---

## Architecture

1. **Fetch** — `news_fetcher.py` pulls and normalizes articles into `news_data/`.
2. **Analyze** — `analysis.py` calls OpenAI to summarize/tag/sentiment, writing JSON into `analysis_results/`.
3. **Embed + Index** — `vector_db.py` creates embeddings and writes a **single JSON** index into `vector_db/`.
4. **Query** — `search_interface.py` loads the index and serves an **interactive CLI** (semantic search & simple RAG).

---

## Repository Layout

```
news_fetcher_ds/
├─ news_fetcher/           # core package: configs/utilities/fetch helpers
├─ news_fetcher.py         # stage 1: fetch sources → news_data/
├─ analysis.py             # stage 2: LLM analysis → analysis_results/
├─ vector_db.py            # stage 3: embeddings + on-disk index (JSON) → vector_db/
├─ search_interface.py     # stage 4: interactive CLI (/search, /ask, /stats, /help)
├─ check_data.py           # quick sanity checks
├─ view_news.py            # pretty-print/inspect combined items
├─ requirements.txt        # dependancies list
├─ .env.example            # environment setting example file
└─ README.md
```
---

## Requirements

* **Python**: 3.9+ (3.11 recommended)
* **OpenAI API key** (for both analysis and embeddings)
* macOS/Linux/Windows supported

---

## Setup (Local)

```bash
# 1) Clone
git clone https://github.com/pmazanik/news_fetcher_ds.git
cd news_fetcher_ds

# 2) Create & activate venv (optional)
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

# 3) Install deps
pip install -U pip
pip install -r requirements.txt

# 4) Configure env
cp .env.example .env
# edit .env and add your OPENAI_API_KEY and other options
```

---

## Quick Start

```bash
# 1) Fetch articles
python news_fetcher.py

# 2) Analyze with OpenAI (summaries, topics, sentiment)
python analysis.py

# 3) Open the interactive semantic search
python search_interface.py

# Try commands in the CLI:
# /search climate change policy
# /ask "What did Reuters say about rate cuts?"
# /stats
# /help
```

---

## Usage

### Fetch

```bash
python news_fetcher.py
```

* Reads configured sources from the package.
* Writes normalized raw items into `news_data/`.

### Analyze

```bash
python analysis.py
```

* Requires `OPENAI_API_KEY`.
* Adds `summary`, `topics`, `sentiment`.
* Outputs per-item JSON files in `analysis_results/`.

### Build/Query (vector DB)

```bash
# The CLI calls this under the hood, but you can use the module directly, e.g.:
python -c "from vector_db import PurePythonVectorDB as DB; d=DB(); d.load_from_disk('vector_db'); print(d.stats())"
```

* Stores an **index.json** (or similar) under `vector_db/` with:

  * header: `embedding_model`, `dimension`, counts, build params
  * `items[]`: metadata + `vector: [float, ...]` (normalized), optional `text_hash`

### Interactive CLI

```bash
python search_interface.py
# /search your query text
# /ask "your question"
# /stats
# /help
# /quit
```

### Utilities

```bash
python check_data.py   # quick counts, existence checks
python view_news.py    # pretty prints combined article info
```

---

## Configuration

Either use environment variables or a `.env` file (copy from `.env.example`). Typical settings:

* `OPENAI_API_KEY` — **required**
* `MODEL` — LLM for analysis (e.g., `gpt-4o-mini`)
* `EMBEDDING_MODEL` — embeddings model (e.g., `text-embedding-3-small`)
* `MAX_ARTICLES_PER_SOURCE` — cap per source (e.g., `20`)
* `REQUEST_DELAY` — polite delay between requests (seconds; e.g., `1.0`)
* (optional) `OUTPUT_DIR`, `ANALYSIS_DIR`, `VECTOR_DB_DIR` — override default folders

---

## Data & Folders

* `news_data/` — raw fetched items (JSON)
* `analysis_results/` — LLM analysis outputs (JSON)
* `vector_db/` — single-file vector index + metadata (JSON)

Mount/persist these when running in Docker to avoid recomputing.

---

## Testing

* basic_test.py - Contains quick smoke tests to check that the core modules (news_fetcher.py, analysis.py, vector_db.py) can be imported and run without errors.
* test_integration.py - Exercises the full pipeline: fetch → analyze → embed → search.
Ensures that data flows correctly between stages and that directories (news_data/, analysis_results/, vector_db/) are populated as expected.
* test_performance.py - Benchmarks embedding and search speed on sample datasets.
Helps detect regressions when scaling to more documents.
* test_semantic.py - Validates the semantic search logic in vector_db.py.
Checks that similar queries return related articles and that cosine similarity is calculated consistently.

---

## Docker (Build & Run)

### 1) Dockerfile (basic)

```dockerfile
# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (leverage layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest
COPY . .

# Non-root user for safety
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default command: open the interactive search CLI
CMD ["python", "search_interface.py"]
```

> Tip: also create a `.dockerignore`:

```
.venv
__pycache__
*.pyc
.env
news_data/
analysis_results/
vector_db/
```

### 2) Build

```bash
docker build -t news-fetcher .
```

### 3) Run each stage (with persistent volumes)

> Create local folders once:

```bash
mkdir -p news_data analysis_results vector_db
```

**Fetch**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher \
  python news_fetcher.py
```

**Analyze**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher \
  python analysis.py
```

**Interactive Search**

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher
# then type /search, /ask, /stats ...
```

You can override envs inline instead of `--env-file .env`, e.g. `-e OPENAI_API_KEY=...`.

---

## Troubleshooting

* **Missing `OPENAI_API_KEY`** → set it in `.env` or pass with `-e OPENAI_API_KEY=...`.
* **Slow or rate-limited analysis** → lower `MAX_ARTICLES_PER_SOURCE`, increase `REQUEST_DELAY`.
* **Empty search results** → ensure you ran **both** fetch and analysis before opening the CLI.
* **Model mismatch** → don’t mix different `EMBEDDING_MODEL`s in the same index; rebuild if you change it.
* **Windows terminal encoding** → use PowerShell and ensure UTF-8 (e.g., `$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()`).

---

## Roadmap

- **Vector search improvements**  
  - Replace the current pure-Python linear scan with a high-performance ANN (Approximate Nearest Neighbor) index such as **FAISS** or **hnswlib**.  
  - Add support for external vector database solutions (**Qdrant**, **Weaviate**, **Pinecone**) to enable scalability beyond tens of thousands of articles.  

- **Framework integration**  
  - Introduce the **LangChain** framework to standardize prompt management, enable Retrieval-Augmented Generation (RAG) pipelines, and simplify orchestration of LLM calls.  
  - Use LangChain retrievers to connect seamlessly with both local and external vector stores.  

- **Enhanced querying**  
  - Add **metadata filtering** (e.g., by source, publication date, sentiment) directly in the CLI or via LangChain retrievers.  
  - Support hybrid search (semantic + keyword) for more precise results.  

- **Performance & efficiency**  
  - Implement **embedding caching** keyed by content hash to avoid redundant API calls.  
  - Allow **incremental updates** to the index instead of full rebuilds.  

- **User experience**  
  - Develop a lightweight **web UI** in addition to the CLI for easier browsing and search.  
  - Provide **Docker Compose** setups for one-command pipeline execution (fetch → analyze → search).
   
---

## License

MIT

---

## Basic Docker Instructions (recap)

1. Put the **Dockerfile** (above) in repo root.
2. `docker build -t news-fetcher .`
3. Create local data dirs and a `.env` with your `OPENAI_API_KEY`.
4. Run **fetch**, then **analyze**, then start the default **search** container (commands above).


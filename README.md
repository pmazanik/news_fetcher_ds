```markdown
# News Fetcher & Semantic Search (pmazanik/news_fetcher_ds)

AI-powered news aggregation and semantic search across multiple sources.  
The pipeline fetches news articles, runs LLM analysis (summaries, topics, sentiment), builds a lightweight vector index, and lets you query the corpus with natural language via an interactive CLI.

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](#)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326ce5.svg)](#)

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Project layout](#project-layout)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data locations](#data-locations)
- [Docker](#docker)
- [Docker Compose (optional)](#docker-compose-optional)
- [Kubernetes](#kubernetes)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Notes & Recommendations](#notes--recommendations)

---

## Features

- Fetches news from multiple reputable sources (see `news_fetcher/config.py`).
- LLM analysis for each article: concise summary, topics, sentiment.
- Pure-Python vector DB for semantic search (no external DB required).
- Interactive CLI for search and question answering over the corpus.
- Works locally, in Docker, and on Kubernetes.

---

## Architecture

```

┌───────────────┐     fetch     ┌───────────────┐
│  RSS/Web Srcs │ ─────────────▶│  news\_fetcher │
└───────────────┘               └───────┬───────┘
│ writes JSON
┌─────▼──────────────┐
│   news\_data/       │
└─────┬──────────────┘
│ analyze (OpenAI)
┌─────▼──────────────┐
│ analysis\_results/  │
└─────┬──────────────┘
│ embed & index
┌─────▼──────────────┐
│   vector\_db/       │
└─────┬──────────────┘
│ interactive query
┌─────▼──────────────┐
│ search\_interface   │
└────────────────────┘

```

---

## Project layout

```

.
├─ news\_fetcher/               # Core package (config, utils, fetchers)
│  ├─ **init**.py
│  ├─ config.py
│  ├─ fetchers.py
│  └─ utils.py
├─ analysis.py                 # LLM analysis pipeline
├─ news\_fetcher.py             # Fetch pipeline entrypoint
├─ vector\_db.py                # Lightweight vector index / semantic search
├─ search\_interface.py         # Interactive CLI (semantic search & Q/A)
├─ view\_news.py                # Simple viewer for combined JSON
├─ check\_data.py               # Diagnostics for data pipeline
├─ requirements.txt
└─ (generated at runtime)
├─ news\_data/
├─ analysis\_results/
└─ vector\_db/

````

---

## Requirements

- Python **3.9+** (3.11 recommended) **or** Docker **20.10+**
- An **OpenAI API key** (set via environment variable)

---

## Installation

Local (development):

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
````

---

## Quick start

### Local

```bash
# 1) Provide OpenAI key for this shell
export OPENAI_API_KEY=...      # Windows PowerShell: $env:OPENAI_API_KEY="..."

# 2) Fetch latest articles (from configured sources)
python news_fetcher.py

# 3) Run LLM analysis (summaries/topics/sentiment)
python analysis.py

# 4) Start the interactive semantic search
python search_interface.py
```

### Docker

```bash
# Build image from repository root
docker build -t news-fetcher:latest .

# Fetch
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher:latest python news_fetcher.py

# Analyze
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher:latest python analysis.py

# Search (interactive)
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$(pwd)/news_data:/app/news_data" \
  -v "$(pwd)/analysis_results:/app/analysis_results" \
  -v "$(pwd)/vector_db:/app/vector_db" \
  news-fetcher:latest python search_interface.py
```

---

## Configuration

You can set options via environment variables (defaults are coded in the project):

* `OPENAI_API_KEY` – **required** for analysis.
* `MAX_ARTICLES_PER_SOURCE` – number of items pulled per source (e.g., `20`).
* `REQUEST_DELAY` – politeness delay between requests in seconds (e.g., `1.0`).
* `MODEL` – LLM for summaries/topics/sentiment (e.g., `gpt-4o-mini`).
* `EMBEDDING_MODEL` – embeddings model (e.g., `text-embedding-3-small`).
* `OUTPUT_DIR`, `ANALYSIS_DIR`, `VECTOR_DB_DIR` – on-disk directories.

To add or customize news sources, edit `news_fetcher/config.py` (and `news_fetcher/fetchers.py` if a custom fetcher is needed).

---

## Usage

### Interactive CLI commands

Run `python search_interface.py`, then:

```
/search climate change       # semantic search
/ask "What did Reuters say?" # question answering
/stats                       # show DB stats
/help                        # list commands
/quit                        # exit
```

### Programmatic example

```python
from vector_db import PurePythonVectorDB

db = PurePythonVectorDB()
db.load_from_disk("vector_db")

results = db.semantic_search("renewable energy investments", k=5)
for r in results:
    print(r["title"], f"{r['similarity']:.3f}")
```

---

## Data locations

* Raw fetched data: `news_data/`
* LLM analysis outputs: `analysis_results/`
* Vector index files: `vector_db/`

These directories are created automatically if missing. When running in containers, mount them as volumes for persistence.

---

## Docker

### Example Dockerfile

If you need a Dockerfile, use this:

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .
RUN useradd -m -u 10001 appuser
USER appuser

VOLUME ["/app/news_data", "/app/analysis_results", "/app/vector_db"]

ENTRYPOINT ["python"]
CMD ["search_interface.py"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,sys; sys.exit(0 if os.path.isdir('vector_db') else 1)"
```

### .dockerignore (recommended)

```
.venv
__pycache__/
*.py[cod]
*.log
.env
.git
.gitignore
dist/
build/
*.egg-info/
news_data/
analysis_results/
vector_db/
```

---

## Docker Compose (optional)

Create `docker-compose.yml` if you prefer a multi-step pipeline:

```yaml
version: "3.9"
services:
  fetch:
    image: news-fetcher:latest
    build: .
    environment:
      - OPENAI_API_KEY
    command: ["news_fetcher.py"]
    volumes:
      - ./news_data:/app/news_data
      - ./analysis_results:/app/analysis_results
      - ./vector_db:/app/vector_db

  analyze:
    image: news-fetcher:latest
    environment:
      - OPENAI_API_KEY
    command: ["analysis.py"]
    depends_on: [fetch]
    volumes:
      - ./news_data:/app/news_data
      - ./analysis_results:/app/analysis_results
      - ./vector_db:/app/vector_db

  search:
    image: news-fetcher:latest
    environment:
      - OPENAI_API_KEY
    command: ["search_interface.py"]
    stdin_open: true
    tty: true
    depends_on: [analyze]
    volumes:
      - ./news_data:/app/news_data
      - ./analysis_results:/app/analysis_results
      - ./vector_db:/app/vector_db
```

Usage:

```bash
docker compose up --build fetch
docker compose run --rm analyze
docker compose run --rm search
```

---

## Kubernetes

Works on minikube, k3d, and managed clusters.

### Build and load image (minikube example)

```bash
minikube start
eval "$(minikube -p minikube docker-env)"
docker build -t news-fetcher:latest .
```

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: news
```

Apply:

```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: news
YAML
```

### Secret (OpenAI key)

Create from your local environment variable:

```bash
kubectl -n news create secret generic openai-secret \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
```

### ConfigMap (tuning)

```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: news-config
  namespace: news
data:
  MAX_ARTICLES_PER_SOURCE: "20"
  REQUEST_DELAY: "1.0"
  MODEL: "gpt-4o-mini"
  EMBEDDING_MODEL: "text-embedding-3-small"
  OUTPUT_DIR: "news_data"
  ANALYSIS_DIR: "analysis_results"
  VECTOR_DB_DIR: "vector_db"
YAML
```

### (Optional) PersistentVolumeClaim

```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: news-pvc
  namespace: news
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 2Gi
YAML
```

### Deployment

```bash
kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: news-app
  namespace: news
spec:
  replicas: 1
  selector:
    matchLabels:
      app: news-app
  template:
    metadata:
      labels:
        app: news-app
    spec:
      containers:
        - name: news
          image: news-fetcher:latest
          imagePullPolicy: IfNotPresent
          envFrom:
            - secretRef:
                name: openai-secret
            - configMapRef:
                name: news-config
          args: ["search_interface.py"]  # default entry (override for batch runs)
          volumeMounts:
            - name: data
              mountPath: /app/news_data
              subPath: news_data
            - name: data
              mountPath: /app/analysis_results
              subPath: analysis_results
            - name: data
              mountPath: /app/vector_db
              subPath: vector_db
          readinessProbe:
            exec:
              command: ["python", "-c", "import os,sys; sys.exit(0 if os.path.isdir('vector_db') else 1)"]
            initialDelaySeconds: 10
            periodSeconds: 15
          livenessProbe:
            exec:
              command: ["python", "-c", "import os,sys; sys.exit(0)"]
            initialDelaySeconds: 30
            periodSeconds: 30
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: news-pvc
YAML
```

### (Optional) Service (for future HTTP UI)

```bash
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: news-svc
  namespace: news
spec:
  type: ClusterIP
  selector:
    app: news-app
  ports:
    - name: http
      port: 80
      targetPort: 8080
YAML
```

### Run one-off jobs in-cluster

```bash
# Fetch
kubectl -n news run fetch --image=news-fetcher:latest --restart=Never \
  --env="OPENAI_API_KEY=$(kubectl -n news get secret openai-secret -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)" \
  -- python news_fetcher.py

# Analyze
kubectl -n news run analyze --image=news-fetcher:latest --restart=Never \
  --env="OPENAI_API_KEY=$(kubectl -n news get secret openai-secret -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)" \
  -- python analysis.py

# Interactive search (ephemeral pod)
kubectl -n news run search --image=news-fetcher:latest --rm -it --restart=Never \
  --env="OPENAI_API_KEY=$(kubectl -n news get secret openai-secret -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)" \
  -- sh -lc "python search_interface.py"
```

---

## Testing

Local:

```bash
python test_performance.py
python test_search.py
python test_semantic.py
python test_integration.py
python basic_test.py
python check_data.py
python view_news.py
```

Docker:

```bash
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  news-fetcher:latest python test_performance.py
```

---

## Troubleshooting

**No results in search**
Run the pipeline first:

```bash
python news_fetcher.py
python analysis.py
```

**401 / OpenAI key errors**
Ensure `OPENAI_API_KEY` is set in your environment or Kubernetes Secret.

**Rate limited**
Increase `REQUEST_DELAY` or reduce `MAX_ARTICLES_PER_SOURCE`.

**Docker build fails**
Rebuild without cache:

```bash
docker build --no-cache -t news-fetcher:latest .
```

**Kubernetes CrashLoopBackOff**
Inspect logs and objects:

```bash
kubectl -n news logs deploy/news-app
kubectl -n news get all
```

---

## Notes & Recommendations

* Prefer stdout logging for containers; avoid writing logs to image layers.
* Keep API keys in env/Secrets only (never in code or images).
* Mount `news_data/`, `analysis_results/`, and `vector_db/` to persist across runs.
* For managed clusters, push `news-fetcher:latest` to a container registry and update the `image:` in Deployment accordingly.

---


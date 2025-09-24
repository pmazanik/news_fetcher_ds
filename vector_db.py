#!/usr/bin/env python3
"""
vector_db.py
Stage 3: Build and query a local vector database (Chroma) using LangChain.

Updates in this version:
- Telemetry completely disabled (env + logger) without removing any packages.
- Removed explicit persist() to avoid Chroma 0.4.x deprecation warning.
- Metadata sanitized to scalars (lists -> comma-separated strings).
"""

from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Any, List

# --- Disable Chroma/PostHog telemetry BEFORE importing chromadb --------------
# We force-disable here so you don't have to manage it in your shell.
os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_ANONYMIZED_TELEMETRY"] = "FALSE"
os.environ["CHROMA_TELEMETRY_IMPL"] = "noop"
os.environ["POSTHOG_DISABLED"] = "1"

# Silence the telemetry loggers (belt & suspenders)
for name in (
    "chromadb.telemetry",
    "chromadb.telemetry.product",
    "chromadb.telemetry.product.posthog",
):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.handlers = [logging.NullHandler()]
    logger.setLevel(logging.CRITICAL)

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

import chromadb
from chromadb.config import Settings  # for telemetry + persistence settings

ANALYSIS_DIR = Path(os.getenv("ANALYSIS_DIR", "analysis_results"))
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION = os.getenv("CHROMA_COLLECTION", "news_articles")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Chroma client settings: persistent storage + telemetry OFF
CLIENT_SETTINGS = Settings(
    anonymized_telemetry=False,
    is_persistent=True,
    persist_directory=CHROMA_DIR,
)

def _sanitize_metadata(meta: dict) -> dict:
    """Chroma metadata must be str|int|float|bool (no lists/dicts/None)."""
    clean: dict[str, Any] = {}
    for k, v in (meta or {}).items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = ", ".join(map(str, v))
        else:
            clean[k] = str(v)
    return clean


class PureChromaVectorDB:
    """
    Wrapper around LangChain's Chroma vectorstore:

      - build(): upsert from latest analysis_results/*.jsonl
      - search(): similarity search
      - stats(): report collection info
    """

    def __init__(self) -> None:
        self.persist_directory = CHROMA_DIR
        self.collection_name = COLLECTION
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self._vs: Chroma | None = None

    def _latest_file(self) -> Path | None:
        files = sorted(ANALYSIS_DIR.glob("*.jsonl"), reverse=True)
        return files[0] if files else None

    def _load_vectorstore(self) -> Chroma:
        if self._vs is None:
            self._vs = Chroma(
                collection_name=self.collection_name,
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                client_settings=CLIENT_SETTINGS,
            )
        return self._vs

    def build(self) -> dict[str, Any]:
        """Build (or rebuild) the vector store from the latest analysis JSONL."""
        path = self._latest_file()
        if not path:
            raise FileNotFoundError("No analysis_results/*.jsonl found")

        docs: List[Document] = []
        ids: List[str] = []

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)

                # Content to index: prefer summary, then full content, then description/title
                text = (
                    rec.get("summary")
                    or rec.get("content")
                    or rec.get("description")
                    or rec.get("title")
                    or ""
                )
                content = f"{rec.get('title','')}\n\n{text}".strip()
                if not content:
                    continue

                meta = _sanitize_metadata({
                    "id": rec.get("id"),
                    "source": rec.get("source"),
                    "url": rec.get("url"),
                    "published_at": rec.get("published_at"),
                    "topics": rec.get("topics") or [],
                    "sentiment": rec.get("sentiment") or "Neutral",
                })

                docs.append(Document(page_content=content, metadata=meta))
                ids.append(str(rec.get("id")))

        # Chroma 0.4.x persists automatically; no explicit persist() call needed
        vs = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=self.persist_directory,
            ids=ids,
            client_settings=CLIENT_SETTINGS,
        )
        self._vs = vs

        return {"count": len(docs), "collection": self.collection_name, "dir": self.persist_directory}

    def _vs_or_raise(self) -> Chroma:
        return self._load_vectorstore()

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Return top-k results with metadata + scores."""
        vs = self._vs_or_raise()
        docs_and_scores = vs.similarity_search_with_score(query, k=k)
        out = []
        for d, score in docs_and_scores:
            out.append({
                "text": d.page_content,
                "score": float(score),
                **(d.metadata or {})
            })
        return out

    def stats(self) -> dict[str, Any]:
        """Return basic stats (telemetry disabled via Settings)."""
        client = chromadb.PersistentClient(path=self.persist_directory, settings=CLIENT_SETTINGS)
        coll = client.get_or_create_collection(self.collection_name, metadata={"hnsw:space": "cosine"})
        return {
            "collection": self.collection_name,
            "persist_directory": self.persist_directory,
            "points_count": coll.count(),
        }


if __name__ == "__main__":
    db = PureChromaVectorDB()
    res = db.build()
    print("Built:", res)
    print("Stats:", db.stats())
    print("Sample search:", db.search("rate cuts and inflation", k=3))


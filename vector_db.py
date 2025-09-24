#!/usr/bin/env python3
"""
vector_db.py
Stage 3: Build and query a real vector database (Qdrant) using LangChain.

- Reads latest analysis_results/*.jsonl
- Embeds with OpenAIEmbeddings
- Upserts into Qdrant (payload contains metadata)
- Exposes PureQdrantVectorDB with .build(), .search(), .stats()
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant as LCQdrant
from langchain.docstore.document import Document

load_dotenv()

ANALYSIS_DIR = Path(os.getenv("ANALYSIS_DIR", "analysis_results"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "news_articles")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

class PureQdrantVectorDB:
    def __init__(self) -> None:
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self._vs = None

    def _ensure_collection(self, dim: int = 1536) -> None:
        if COLLECTION not in [c.name for c in self.client.get_collections().collections]:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def _latest_file(self) -> Path | None:
        files = sorted(ANALYSIS_DIR.glob("*.jsonl"), reverse=True)
        return files[0] if files else None

    def build(self) -> dict[str, Any]:
        path = self._latest_file()
        if not path:
            raise FileNotFoundError("No analysis_results/*.jsonl found")

        docs: list[Document] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                text = rec.get("summary") or rec.get("description") or rec.get("title") or ""
                content = f"{rec.get('title','')}\n\n{text}"
                meta = {
                    "id": rec["id"],
                    "source": rec.get("source"),
                    "url": rec.get("url"),
                    "published_at": rec.get("published_at"),
                    "topics": rec.get("topics") or [],
                    "sentiment": rec.get("sentiment") or "Neutral",
                }
                docs.append(Document(page_content=content, metadata=meta))

        # Create collection (Qdrant auto-detect dims from first embedding if not specified by LC)
        self._ensure_collection()
        self._vs = LCQdrant.from_documents(
            documents=docs,
            embedding=self.embeddings,
            url=QDRANT_URL,
            prefer_grpc=False,
            api_key=QDRANT_API_KEY,
            collection_name=COLLECTION,
        )
        return {"count": len(docs), "collection": COLLECTION}

    def _vs_or_raise(self):
        if self._vs is None:
            # lazy load vectorstore handle for querying
            self._vs = LCQdrant(
                client=self.client, collection_name=COLLECTION, embeddings=self.embeddings
            )
        return self._vs

    def search(self, query: str, k: int = 5, **filters) -> list[dict]:
        vs = self._vs_or_raise()
        docs = vs.similarity_search(query, k=k)
        out = []
        for d in docs:
            out.append({
                "text": d.page_content,
                "score": getattr(d, "score", None),
                **(d.metadata or {})
            })
        return out

    def stats(self) -> dict[str, Any]:
        info = self.client.get_collection(COLLECTION)
        return {
            "collection": COLLECTION,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
        }

if __name__ == "__main__":
    db = PureQdrantVectorDB()
    res = db.build()
    print("Built:", res)
    print("Stats:", db.stats())
    print("Sample search:", db.search("rate cuts and inflation", k=3))

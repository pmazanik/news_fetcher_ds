#!/usr/bin/env python3
"""
analysis.py
Stage 2: Use LLM to enrich items with summary, topics, sentiment.

- LangChain ChatOpenAI pipeline
- Batching + retries
- Writes JSONL to analysis_results/
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

INPUT_DIR = Path(os.getenv("OUTPUT_DIR", "news_data"))
OUT_DIR = Path(os.getenv("ANALYSIS_DIR", "analysis_results"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("MODEL", "gpt-4o-mini")

class EnrichedItem(BaseModel):
    id: str
    source: str
    url: str
    title: str
    description: str | None = None
    content_hash: str
    published_at: str | None = None

    summary: str | None = None
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a concise analyst. Summarize the article in 2-3 sentences, propose 3-5 topical tags, "
     "and label overall sentiment as Positive/Neutral/Negative."),
    ("human", "Title: {title}\nDescription: {description}\nURL: {url}\n\nReturn JSON with keys: summary, topics (array), sentiment.")
])

llm = ChatOpenAI(model=MODEL, temperature=0.2)

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1.0, 3.0))
def _call_llm(title: str, description: str | None, url: str) -> dict:
    chain = prompt | llm
    resp = chain.invoke({"title": title, "description": description or "", "url": url})
    # Try to parse JSON from content; if not JSON, heuristic fallback
    txt = resp.content.strip()
    try:
        return json.loads(txt)
    except Exception:
        # crude fallback extraction
        return {"summary": txt[:600], "topics": [], "sentiment": "Neutral"}

def _iter_latest_jsonl(dirpath: Path) -> Iterable[Path]:
    files = sorted(dirpath.glob("*.jsonl"), reverse=True)
    if files:
        yield files[0]

def main() -> None:
    in_files = list(_iter_latest_jsonl(INPUT_DIR))
    if not in_files:
        print("No input files in news_data/")
        return
    in_file = in_files[0]
    out_file = OUT_DIR / in_file.name.replace("news_", "analysis_")

    with in_file.open("r", encoding="utf-8") as fin, out_file.open("w", encoding="utf-8") as fout:
        for line in fin:
            raw = json.loads(line)
            enriched = EnrichedItem(**raw)
            info = _call_llm(enriched.title, enriched.description, enriched.url)
            enriched.summary = info.get("summary")
            enriched.topics = info.get("topics") or []
            enriched.sentiment = info.get("sentiment") or "Neutral"
            fout.write(enriched.model_dump_json() + "\n")

    print(f"Wrote enriched data to {out_file}")

if __name__ == "__main__":
    main()

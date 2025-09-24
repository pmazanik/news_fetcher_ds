#!/usr/bin/env python3
"""
analysis.py
Stage 2: Use LLM (LangChain + OpenAI) to enrich items with summary, topics, sentiment.

Now token-safe:
- If an article is short -> single-shot summary (as before).
- If long -> chunk into overlapping pieces, summarize each chunk, then combine into a final JSON.
- Progress-friendly (tqdm), periodic throughput, and clear final summary.

Environment toggles:
  MODEL=gpt-4o-mini
  OUTPUT_DIR=news_data
  ANALYSIS_DIR=analysis_results
  ANALYSIS_LOG_EVERY=50
  ANALYSIS_MAX_ITEMS=0            # 0 = process all

  # Chunking & limits (character-based; keeps us under context window)
  ANALYSIS_SINGLE_SHOT_CHARS=12000
  ANALYSIS_CHUNK_CHARS=6000
  ANALYSIS_CHUNK_OVERLAP=500
  ANALYSIS_MAX_CHUNKS=10          # cap the number of chunk summaries used for combine

Notes:
- We keep everything dependency-light: pure character-based chunking (no extra token libs).
- If your model has a very small context, lower SINGLE_SHOT_CHARS and CHUNK_CHARS accordingly.
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

load_dotenv()

INPUT_DIR = Path(os.getenv("OUTPUT_DIR", "news_data"))
OUT_DIR = Path(os.getenv("ANALYSIS_DIR", "analysis_results"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("MODEL", "gpt-4o-mini")
LOG_EVERY = int(os.getenv("ANALYSIS_LOG_EVERY", "50"))
MAX_ITEMS = int(os.getenv("ANALYSIS_MAX_ITEMS", "0"))  # 0 = all

# Token-safety & chunking
SINGLE_SHOT_CHAR_LIMIT = int(os.getenv("ANALYSIS_SINGLE_SHOT_CHARS", "12000"))
CHUNK_CHARS = int(os.getenv("ANALYSIS_CHUNK_CHARS", "6000"))
CHUNK_OVERLAP = int(os.getenv("ANALYSIS_CHUNK_OVERLAP", "500"))
MAX_CHUNKS = int(os.getenv("ANALYSIS_MAX_CHUNKS", "10"))

class EnrichedItem(BaseModel):
    id: str
    source: str
    url: str
    title: str
    description: str | None = None
    content: str | None = None
    content_hash: str
    published_at: str | None = None

    summary: str | None = None
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None

# Prompts
SINGLE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a concise analyst. Summarize the article in 3–4 sentences, propose 3–5 topical tags, "
     "and label overall sentiment as Positive/Neutral/Negative. Return valid JSON with keys: "
     "summary, topics (array), sentiment."),
    ("human",
     "Title: {title}\n\n"
     "Article text (may be truncated):\n{article_text}")
])

CHUNK_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert condensing assistant. The user will send PART of an article. "
     "Write a tight 2–3 sentence summary capturing only the most important facts from this PART. "
     "Return plain text only (no JSON, no bullet points)."),
    ("human",
     "Title: {title}\n\nArticle CHUNK:\n{chunk_text}")
])

COMBINE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You will receive multiple short summaries from different parts of the SAME article. "
     "Write ONE overall 3–4 sentence summary (avoid repetition), propose 3–5 topical tags, "
     "and set sentiment as Positive/Neutral/Negative. Return valid JSON with keys: "
     "summary, topics (array), sentiment."),
    ("human",
     "Title: {title}\n\nChunk summaries (each corresponds to a different part of the article):\n{chunk_summaries}")
])

# LLM client
llm = ChatOpenAI(model=MODEL, temperature=0.2)

# --- Helpers -----------------------------------------------------------------

def _latest_jsonl(dirpath: Path) -> Path | None:
    files = sorted(dirpath.glob("*.jsonl"), reverse=True)
    return files[0] if files else None

def _best_text(enriched: EnrichedItem) -> str:
    """Prefer full content, else description, else title."""
    return (enriched.content or enriched.description or enriched.title or "")

def _chunk_text(text: str, size: int, overlap: int) -> List[str]:
    """Simple character-based chunker with overlap."""
    if size <= 0:
        return [text]
    if overlap < 0:
        overlap = 0
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n and len(chunks) < MAX_CHUNKS + 5:  # hard stop to avoid runaway
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap if end - overlap > start else end
    # Respect MAX_CHUNKS cap
    if len(chunks) > MAX_CHUNKS:
        chunks = chunks[:MAX_CHUNKS]
    return chunks

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1.0, 3.0))
def _call_llm_json(title: str, article_text: str) -> dict:
    """Single-shot JSON (short articles)."""
    chain = SINGLE_PROMPT | llm
    resp = chain.invoke({"title": title, "article_text": article_text})
    txt = (resp.content or "").strip()
    try:
        return json.loads(txt)
    except Exception:
        # If model didn't return JSON, keep something useful
        return {"summary": txt[:800], "topics": [], "sentiment": "Neutral"}

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1.0, 3.0))
def _summarize_chunk(title: str, chunk_text: str) -> str:
    """Summarize a single chunk into 2–3 sentences (plain text)."""
    chain = CHUNK_PROMPT | llm
    resp = chain.invoke({"title": title, "chunk_text": chunk_text})
    return (resp.content or "").strip()

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1.0, 3.0))
def _combine_summaries(title: str, chunk_summaries: List[str]) -> dict:
    """Combine chunk summaries into final JSON: {summary, topics[], sentiment}."""
    chain = COMBINE_PROMPT | llm
    joined = "\n\n".join(chunk_summaries)
    resp = chain.invoke({"title": title, "chunk_summaries": joined})
    txt = (resp.content or "").strip()
    try:
        return json.loads(txt)
    except Exception:
        return {"summary": txt[:800], "topics": [], "sentiment": "Neutral"}

def _analyze_text(title: str, article_text: str, notify: callable | None = None) -> dict:
    """Choose single-shot vs chunked summarization."""
    if len(article_text) <= SINGLE_SHOT_CHAR_LIMIT:
        return _call_llm_json(title, article_text[:SINGLE_SHOT_CHAR_LIMIT])

    # Chunked path
    chunks = _chunk_text(article_text, CHUNK_CHARS, CHUNK_OVERLAP)
    if notify:
        notify(f"[analysis] Long article: chunking into {len(chunks)} parts")

    mini_summaries: List[str] = []
    for i, ch in enumerate(chunks, start=1):
        s = _summarize_chunk(title, ch)
        # ensure non-empty; keep it short-ish to protect the combine step
        s = (s or "").strip()
        if not s:
            continue
        if len(s) > 1200:  # safety: avoid very long chunk summaries
            s = s[:1200]
        mini_summaries.append(s)

    if not mini_summaries:
        # Fallback: at least try a truncated single-shot
        return _call_llm_json(title, article_text[:SINGLE_SHOT_CHAR_LIMIT])

    return _combine_summaries(title, mini_summaries)

# --- Main --------------------------------------------------------------------

def main() -> None:
    in_file = _latest_jsonl(INPUT_DIR)
    if not in_file:
        print(f"[analysis] No input files in {INPUT_DIR}/", file=sys.stderr)
        sys.exit(2)

    out_file = OUT_DIR / in_file.name.replace("news_", "analysis_")

    # Count lines first for a proper progress bar
    with in_file.open("r", encoding="utf-8") as f:
        total = sum(1 for _ in f)

    if MAX_ITEMS > 0:
        total = min(total, MAX_ITEMS)

    start_ts = time.time()
    print("=" * 72)
    print(f"[analysis] Starting (token-safe mode)")
    print(f"  Model:                     {MODEL}")
    print(f"  Input:                     {in_file}")
    print(f"  Output:                    {out_file}")
    print(f"  Items:                     {total} {'(limited)' if MAX_ITEMS > 0 else ''}")
    print(f"  SINGLE_SHOT_CHAR_LIMIT:    {SINGLE_SHOT_CHAR_LIMIT}")
    print(f"  CHUNK_CHARS / OVERLAP:     {CHUNK_CHARS} / {CHUNK_OVERLAP}")
    print(f"  MAX_CHUNKS:                {MAX_CHUNKS}")
    print("=" * 72, flush=True)

    processed = 0
    succeeded = 0
    failed = 0
    last_report = start_ts

    with in_file.open("r", encoding="utf-8") as fin, out_file.open("w", encoding="utf-8") as fout:
        pbar = tqdm(total=total, desc="Analyzing", unit="item")
        for i, line in enumerate(fin, start=1):
            if MAX_ITEMS > 0 and processed >= MAX_ITEMS:
                break

            try:
                raw = json.loads(line)
            except Exception as e:
                failed += 1
                processed += 1
                pbar.update(1)
                if processed % LOG_EVERY == 0:
                    elapsed = time.time() - last_report
                    rate = LOG_EVERY / elapsed if elapsed > 0 else 0.0
                    tqdm.write(f"[analysis] {processed}/{total}: parse error ({e.__class__.__name__}); ~{rate:.1f} it/s")
                    last_report = time.time()
                continue

            try:
                enriched = EnrichedItem(**raw)
                # Prefer full content, then description, then title
                article_text = _best_text(enriched)
                # Main logic (single vs chunked)
                info = _analyze_text(
                    title=enriched.title,
                    article_text=article_text,
                    notify=lambda msg: tqdm.write(msg)
                )
                enriched.summary = info.get("summary")
                enriched.topics = info.get("topics") or []
                enriched.sentiment = info.get("sentiment") or "Neutral"
                fout.write(enriched.model_dump_json() + "\n")
                succeeded += 1
            except Exception as e:
                failed += 1
                tqdm.write(f"[analysis] Item failed ({e.__class__.__name__}: {e})")

            processed += 1
            pbar.update(1)

            # periodic lightweight status
            if processed % LOG_EVERY == 0:
                now = time.time()
                elapsed = now - last_report
                rate = LOG_EVERY / elapsed if elapsed > 0 else 0.0
                tqdm.write(f"[analysis] {processed}/{total} processed | ok={succeeded} fail={failed} | ~{rate:.1f} it/s")
                last_report = now

        pbar.close()

    wall = time.time() - start_ts
    print("-" * 72)
    print(f"[analysis] Done")
    print(f"  Output file:  {out_file}")
    print(f"  Processed:    {processed}/{total}")
    print(f"  Succeeded:    {succeeded}")
    print(f"  Failed:       {failed}")
    print(f"  Elapsed:      {wall:.1f}s  (~{processed / wall if wall > 0 else 0:.2f} it/s)")
    print("-" * 72, flush=True)

if __name__ == "__main__":
    main()

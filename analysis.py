#!/usr/bin/env python3
"""
analysis.py
Stage 2: Use LLM to enrich items with summary, topics, sentiment.

What's new:
- Verbose, user-friendly progress output with tqdm.
- Start/end banners with file paths and model info.
- Per-item error handling and counters (won't silently stall).
- Final summary with timings and throughput.

Env toggles:
  MODEL=gpt-4o-mini            # LLM model
  OUTPUT_DIR=news_data         # input dir (JSONL)
  ANALYSIS_DIR=analysis_results# output dir (JSONL)
  ANALYSIS_LOG_EVERY=50        # print a short status line every N items
  ANALYSIS_MAX_ITEMS=0         # limit items for quick runs (0 = no limit)
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable

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

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a concise analyst. Summarize the article in 3-4 sentences, propose 3-5 topical tags, "
     "and label overall sentiment as Positive/Neutral/Negative."),
    ("human",
     "Title: {title}\n\n"
     "Article text (may be truncated):\n{article_text}\n\n"
     "Return JSON with keys: summary, topics (array), sentiment."
    )
])

llm = ChatOpenAI(model=MODEL, temperature=0.2)

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1.0, 3.0))
def _call_llm(title: str, article_text: str) -> dict:
    chain = prompt | llm
    resp = chain.invoke({"title": title, "article_text": article_text})
    txt = (resp.content or "").strip()
    try:
        return json.loads(txt)
    except Exception:
        # If model didn't return JSON, keep something useful
        return {"summary": txt[:800], "topics": [], "sentiment": "Neutral"}

def _latest_jsonl(dirpath: Path) -> Path | None:
    files = sorted(dirpath.glob("*.jsonl"), reverse=True)
    return files[0] if files else None

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
    print(f"[analysis] Starting")
    print(f"  Model:        {MODEL}")
    print(f"  Input:        {in_file}")
    print(f"  Output:       {out_file}")
    print(f"  Items:        {total} {'(limited)' if MAX_ITEMS > 0 else ''}")
    print("=" * 72, flush=True)

    processed = 0
    succeeded = 0
    failed = 0
    last_report = start_ts

    # Process records with a progress bar
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
                article_text = (enriched.content or enriched.description or enriched.title or "")[:8000]
                info = _call_llm(enriched.title, article_text)
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


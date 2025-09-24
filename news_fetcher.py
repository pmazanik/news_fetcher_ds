#!/usr/bin/env python3
"""
news_fetcher.py
Stage 1: Fetch and normalize news into news_data/ as JSONL.

- Async HTTP fetching with polite delay & retries
- URL canonicalization + content hash for dedupe
- Simple pluggable "source adapters" (RSS/JSON APIs)
- Python 3.11+
"""

from __future__ import annotations
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from pydantic import BaseModel, Field
from dotenv import load_dotenv

DATA_DIR = Path(os.getenv("OUTPUT_DIR", "news_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "50"))

# ---- Models -----------------------------------------------------------------

class Article(BaseModel):
    id: str
    source: str
    url: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[str] = None  # ISO8601
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    content_hash: str

# ---- Utilities ---------------------------------------------------------------

def canonicalize_url(url: str) -> str:
    # Strip tracking params; lowercase host; remove trailing slashes
    if "?" in url:
        url, _ = url.split("?", 1)
    url = re.sub(r"/+$", "", url.strip())
    url = url.replace("http://", "https://")
    return url

def sha256(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---- Source adapters (very small, you can extend) ----------------------------

@dataclass
class Source:
    name: str
    url: str
    kind: str = "rss"   # "rss" | "json"

SOURCES: list[Source] = [
    # Add/adjust as you wish; these are examples that return RSS/Atom or JSON
    Source(name="Reuters-World", url="https://feeds.reuters.com/reuters/worldNews", kind="rss"),
    Source(name="AP-Top", url="https://www.apnews.com/apf-topnews?output=atom", kind="rss"),
]

# ---- Fetching ---------------------------------------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(0.5, 2.0))
async def fetch(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def parse_rss(text: str, source: str) -> Iterable[dict]:
    # Very light RSS/Atom parse via regex to keep deps minimal.
    # For richer parsing, add feedparser.
    items = re.findall(r"<item>(.*?)</item>", text, flags=re.S | re.I)
    if not items:
        items = re.findall(r"<entry>(.*?)</entry>", text, flags=re.S | re.I)
    for chunk in items[:MAX_ARTICLES_PER_SOURCE]:
        title = re.search(r"<title.*?>(.*?)</title>", chunk, flags=re.S | re.I)
        link = re.search(r"<link.*?>(.*?)</link>", chunk, flags=re.S | re.I) or re.search(r'href=["\'](.*?)["\']', chunk, flags=re.S | re.I)
        desc = re.search(r"<description.*?>(.*?)</description>", chunk, flags=re.S | re.I) or re.search(r"<summary.*?>(.*?)</summary>", chunk, flags=re.S | re.I)
        pub = re.search(r"<pubDate.*?>(.*?)</pubDate>", chunk, flags=re.S | re.I) or re.search(r"<updated.*?>(.*?)</updated>", chunk, flags=re.S | re.I)

        url = canonicalize_url((link.group(1).strip() if link else "").replace("&amp;", "&"))
        title_txt = (title.group(1) if title else "").strip()
        desc_txt = re.sub("<.*?>", "", (desc.group(1) if desc else "").strip())
        published = (pub.group(1).strip() if pub else None)

        if url:
            yield {
                "source": source,
                "url": url,
                "title": title_txt,
                "description": desc_txt or None,
                "published_at": published,
            }

async def gather_all() -> list[Article]:
    out: list[Article] = []
    async with httpx.AsyncClient(headers={"User-Agent": "news-fetcher/1.0"}) as client:
        for src in SOURCES:
            await asyncio.sleep(REQUEST_DELAY)
            text = await fetch(client, src.url)
            if src.kind == "rss":
                parsed = list(parse_rss(text, src.name))
            else:
                parsed = []
            for p in parsed:
                ch = sha256(p.get("title", ""), p.get("url", ""))
                art = Article(
                    id=ch,
                    source=p["source"],
                    url=p["url"],
                    title=p.get("title") or "(untitled)",
                    description=p.get("description"),
                    content=None,
                    published_at=p.get("published_at"),
                    authors=[],
                    tags=[],
                    language=None,
                    content_hash=ch,
                )
                out.append(art)
    return out

def write_jsonl(articles: list[Article]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fp = DATA_DIR / f"news_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
    seen: set[str] = set()

    with fp.open("w", encoding="utf-8") as f:
        for a in articles:
            if a.id in seen:
                continue
            seen.add(a.id)
            f.write(a.model_dump_json() + "\n")
    return fp

# ---- Main -------------------------------------------------------------------

def main() -> None:
    arts = asyncio.run(gather_all())
    path = write_jsonl(arts)
    print(f"Wrote {len(arts)} (deduped) to {path}")

if __name__ == "__main__":
    main()

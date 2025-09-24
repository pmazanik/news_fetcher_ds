#!/usr/bin/env python3
"""
news_fetcher.py
Stage 1: Fetch, normalize, and (optionally) fetch full article text into news_data/ as JSONL.

Highlights:
- Robust RSS parsing with `feedparser` (gets title/summary/published/content:encoded).
- If full text not in feed, fetch page HTML and extract with `trafilatura`.
- Async httpx with retries, concurrency limits, and proxy support (trust_env=True).
- FEED_URLS in .env (Name|URL[,rss|json]) with ; or newline separators.
- Controls via .env:
    CONTENT_FETCH=true          # enable HTML content fetching (default: true)
    CONTENT_CONCURRENCY=5       # parallel article fetches
    CONTENT_TIMEOUT=20          # seconds
    MAX_ARTICLES_PER_SOURCE=50
    REQUEST_DELAY=0.3
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
import socket
import sys

import httpx
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import trafilatura

load_dotenv()

DATA_DIR = Path(os.getenv("OUTPUT_DIR", "news_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.3"))
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "50"))

CONTENT_FETCH = os.getenv("CONTENT_FETCH", "true").lower() in {"1", "true", "yes", "on"}
CONTENT_CONCURRENCY = int(os.getenv("CONTENT_CONCURRENCY", "5"))
CONTENT_TIMEOUT = float(os.getenv("CONTENT_TIMEOUT", "20"))

UA = os.getenv("USER_AGENT", "news-fetcher/1.0 (+https://example.local)")

# ---- Models -----------------------------------------------------------------

class Article(BaseModel):
    id: str
    source: str
    url: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[str] = None  # ISO8601 or original feed string
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    content_hash: str

# ---- Utilities ---------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
    print(f"[news_fetcher {ts}] {msg}", flush=True)

def canonicalize_url(url: str) -> str:
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

# ---- Source adapters ---------------------------------------------------------

@dataclass
class Source:
    name: str
    url: str
    kind: str = "rss"   # "rss" | "json"

def _default_sources() -> list[Source]:
    return [
        Source(name="BBC-World", url="https://feeds.bbci.co.uk/news/world/rss.xml", kind="rss"),
        Source(name="CNN-Top", url="http://rss.cnn.com/rss/edition.rss", kind="rss"),
    ]

ENTRY_SPLIT_RE = re.compile(r"[;\n]|,(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)")
ENTRY_RE = re.compile(
    r"""
    ^\s*
    (?P<name>[^|]+?)            # name up to the pipe
    \|
    (?P<url>https?://\S+?)      # URL starting with http(s)
    (?:                         # optional kind, prefixed by comma or whitespace
        (?:\s+|,)
        (?P<kind>rss|json)
    )?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def _sources_from_env() -> list[Source]:
    raw = os.getenv("FEED_URLS", "").strip()
    if not raw:
        return []
    entries = [e for e in ENTRY_SPLIT_RE.split(raw) if e and e.strip() and "|" in e]
    out: list[Source] = []
    for e in entries:
        token = e.strip().strip('"\'')

        low = token.lower()
        if low in {"rss", "json"}:
            continue

        m = ENTRY_RE.match(token)
        if not m:
            log(f"Warn: could not parse FEED_URLS entry: {e!r}")
            continue

        name = m.group("name").strip()
        url = m.group("url").strip().replace("&amp;", "&")
        kind = (m.group("kind") or "rss").lower()
        out.append(Source(name=name, url=url, kind=kind))
    if out:
        log(f"Parsed {len(out)} sources from FEED_URLS")
    return out

SOURCES: list[Source] = _sources_from_env() or _default_sources()

# ---- HTTP helpers ------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(0.5, 2.0),
    retry=retry_if_exception_type((httpx.HTTPError, Exception)),
    reraise=True,
)
async def fetch_text(client: httpx.AsyncClient, url: str, timeout: float = 30.0) -> str:
    r = await client.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

# ---- RSS parsing -------------------------------------------------------------

def _from_feed_entry(entry, src_name: str) -> Article:
    # URL
    url = entry.get("link") or entry.get("id") or ""
    url = canonicalize_url(url)

    # Title/summary
    title = (entry.get("title") or "(untitled)").strip()
    description = (entry.get("summary") or "").strip() or None

    # Authors
    authors = []
    if "author" in entry and entry["author"]:
        authors = [entry["author"]]
    elif "authors" in entry and entry["authors"]:
        authors = [a.get("name") for a in entry["authors"] if a.get("name")]

    # Published
    published = entry.get("published") or entry.get("updated")

    # content:encoded or content[] blocks
    content_text = None
    if "content" in entry and isinstance(entry["content"], list):
        # choose the longest text block
        blocks = [c.get("value") for c in entry["content"] if isinstance(c, dict) and c.get("value")]
        if blocks:
            content_text = max(blocks, key=lambda t: len(t))

    # basic cleanup for description/content (strip tags roughly)
    if description:
        description = re.sub("<.*?>", "", description).strip() or None
    if content_text:
        content_text = re.sub("<.*?>", "", content_text).strip() or None

    ch = sha256(title, url)
    return Article(
        id=ch,
        source=src_name,
        url=url,
        title=title,
        description=description,
        content=content_text,  # may be None; we’ll attempt HTML extraction later
        published_at=published,
        authors=authors,
        tags=[],
        language=None,
        content_hash=ch,
    )

async def parse_feed(client: httpx.AsyncClient, src: Source) -> list[Article]:
    raw = await fetch_text(client, src.url, timeout=30)
    fp = feedparser.parse(raw)
    arts: list[Article] = []
    for entry in (fp.entries or [])[:MAX_ARTICLES_PER_SOURCE]:
        art = _from_feed_entry(entry, src.name)
        arts.append(art)
    return arts

# ---- Article HTML content extraction ----------------------------------------

async def enrich_with_fulltext(client: httpx.AsyncClient, article: Article, semaphore: asyncio.Semaphore) -> None:
    """Fill article.content if empty by fetching HTML and extracting main text."""
    if article.content and len(article.content) > 400:  # already have decent content
        return
    if not CONTENT_FETCH:
        return

    async with semaphore:
        try:
            html = await fetch_text(client, article.url, timeout=CONTENT_TIMEOUT)
        except Exception as e:
            log(f"Warn[{article.source}]: HTML fetch failed for {article.url} -> {type(e).__name__}: {e}")
            return

        try:
            # Trafilatura: extract readable text; pass url for better heuristics
            text = trafilatura.extract(html, url=article.url, include_comments=False, include_tables=False)
            if text:
                # Filter out super short pages or nav-only junk
                clean = text.strip()
                if len(clean) >= 400:
                    article.content = clean
        except Exception as e:
            log(f"Warn[{article.source}]: extraction failed {article.url} -> {type(e).__name__}: {e}")

# ---- Orchestration -----------------------------------------------------------

async def gather_all() -> list[Article]:
    out: list[Article] = []
    failures: list[tuple[str, str]] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": UA},
        follow_redirects=True,
        trust_env=True,
    ) as client:
        # Fetch feeds
        for src in SOURCES:
            await asyncio.sleep(REQUEST_DELAY)
            # DNS hint
            try:
                host = re.sub(r"^https?://", "", src.url).split("/")[0]
                socket.gethostbyname(host)
            except Exception as e:
                log(f"Warn[{src.name}]: DNS resolution failed: {e!r}")

            try:
                if src.kind == "rss":
                    arts = await parse_feed(client, src)
                else:
                    arts = []
                out.extend(arts)
                log(f"OK[{src.name}]: {len(arts)} feed items")
            except Exception as e:
                failures.append((src.name, f"{type(e).__name__}: {e}"))
                log(f"Warn[{src.name}]: feed parse failed -> {type(e).__name__}: {e}")

        # Enrich with article full text
        if CONTENT_FETCH and out:
            sem = asyncio.Semaphore(CONTENT_CONCURRENCY)
            tasks = [enrich_with_fulltext(client, a, sem) for a in out]
            await asyncio.gather(*tasks)

    if failures:
        log("Some sources failed:")
        for name, reason in failures:
            log(f"  - {name}: {reason}")

    return out

def write_jsonl(articles: list[Article]) -> Optional[Path]:
    if not articles:
        log("No articles collected; nothing to write.")
        return None

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

def main() -> None:
    log(f"Starting fetch for {len(SOURCES)} sources (content_fetch={CONTENT_FETCH})")
    arts = asyncio.run(gather_all())
    path = write_jsonl(arts)
    if path:
        have_full = sum(1 for a in arts if a.content and len(a.content) >= 400)
        log(f"Wrote {len(arts)} items (with_fulltext={have_full}) to {path}")
    else:
        log("Completed: 0 articles written. Check network/DNS or FEED_URLS config.")
        sys.exit(2)

if __name__ == "__main__":
    main()


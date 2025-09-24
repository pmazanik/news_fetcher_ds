# tests/conftest.py
# Make tests import the top-level scripts (news_fetcher.py, vector_db.py)
# even if a package directory with the same name exists in the repo.
import os
import sys
import platform
import time
from pathlib import Path
import importlib.util
from typing import List

ROOT = Path(__file__).resolve().parents[1]

def _load_as(modname: str, filename: str):
    """Load a module from a file and register it under `modname`."""
    path = ROOT / filename
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod  # register before exec
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

# Put repo root first on sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Preload our top-level scripts under canonical names
_load_as("news_fetcher", "news_fetcher.py")
_load_as("vector_db", "vector_db.py")

# Disable Chroma/PostHog telemetry during tests (no noisy logs)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
os.environ.setdefault("CHROMA_ANONYMIZED_TELEMETRY", "FALSE")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "noop")
os.environ.setdefault("POSTHOG_DISABLED", "1")

# Avoid failures if tests run without a real OpenAI key
os.environ.setdefault("OPENAI_API_KEY", "test-key")

# ---------- Pretty header & summary ----------

def _pkg_ver(name: str) -> str:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "unknown")
    except Exception:
        return "not-installed"

def _count_sources_from_env() -> int:
    raw = os.getenv("FEED_URLS", "").strip()
    if not raw:
        return 0
    # Split on ; or newline; count entries that contain a pipe (Name|URL)
    parts = [p for p in [s.strip() for s in raw.replace("\r", "").split("\n")] if p]
    items: List[str] = []
    for p in parts:
        if ";" in p:
            items.extend([x for x in p.split(";") if x.strip()])
        else:
            items.append(p)
    return sum(1 for x in items if "|" in x)

def pytest_report_header(config):
    py = platform.python_version()
    sysname = platform.system()
    arch = platform.machine()

    # Key packages
    httpx_ver = _pkg_ver("httpx")
    lc_ver = _pkg_ver("langchain")
    lc_comm_ver = _pkg_ver("langchain_community")
    lc_oa_ver = _pkg_ver("langchain_openai")
    chroma_ver = _pkg_ver("chromadb")

    # Env toggles
    chroma_dir = os.getenv("CHROMA_DIR", "chroma_db")
    chroma_coll = os.getenv("CHROMA_COLLECTION", "news_articles")
    model = os.getenv("MODEL", "gpt-4o-mini")
    content_fetch = os.getenv("CONTENT_FETCH", "true")
    max_per_src = os.getenv("MAX_ARTICLES_PER_SOURCE", "50")
    src_count = _count_sources_from_env()

    lines = [
        f"Python {py} on {sysname} ({arch})",
        f"httpx={httpx_ver}  langchain={lc_ver}  langchain_community={lc_comm_ver}  langchain_openai={lc_oa_ver}  chromadb={chroma_ver}",
        f"MODEL={model}  CONTENT_FETCH={content_fetch}  MAX_ARTICLES_PER_SOURCE={max_per_src}",
        f"Chroma dir={chroma_dir}  collection={chroma_coll}  FEED_URLS entries={src_count or 'default (BBC+etc.)'}",
    ]
    # Remember start time for summary
    config._start_time = time.time()
    return "\n".join(lines)

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    tr = terminalreporter
    stats = tr.stats
    # Counts
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    errors = len(stats.get("error", []))
    skipped = len(stats.get("skipped", []))
    xfailed = len(stats.get("xfailed", []))
    xpassed = len(stats.get("xpassed", []))
    warnings = len(stats.get("warnings", []))
    total = tr._numcollected

    elapsed = 0.0
    if hasattr(config, "_start_time"):
        elapsed = time.time() - config._start_time

    # Build a compact summary line
    parts = [f"total={total}", f"passed={passed}"]
    if failed: parts.append(f"failed={failed}")
    if errors: parts.append(f"errors={errors}")
    if skipped: parts.append(f"skipped={skipped}")
    if xfailed: parts.append(f"xfailed={xfailed}")
    if xpassed: parts.append(f"xpassed={xpassed}")
    if warnings: parts.append(f"warnings={warnings}")
    parts.append(f"time={elapsed:.2f}s")

    tr.write_sep("-", "Test summary")
    tr.write_line(" ".join(parts))
    tr.write_line("Tips: use -vv for more detail, --maxfail=1 to stop early, -k expr to filter tests")


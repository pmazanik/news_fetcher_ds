#!/usr/bin/env python3
"""
search_interface.py
Interactive CLI on top of Chroma + LangChain.

What's new (visibility):
- Startup banner with MODEL, collection, persistence dir, AUTO_BUILD.
- Auto-build on startup if the vector store is empty, with a spinner and before/after stats.
- /rebuild (alias: /refresh) shows a spinner and summary.
- /search and /ask print timing, hit counts, and quick refs for transparency.
- Friendlier /stats output.

Commands:
  /search <query>         - semantic search (shows k, time)
  /ask "<question>"       - RAG-style Q&A from retrieved context (shows time & refs)
  /stats                  - vector DB stats
  /rebuild                - rebuild vectors from latest analysis JSONL
  /help
  /quit
"""

from __future__ import annotations
import os
import shlex
import time
from typing import List

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from langchain_openai import ChatOpenAI
from langchain.schema import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from vector_db import PureChromaVectorDB

# --- Env / setup --------------------------------------------------------------

load_dotenv()
console = Console()

MODEL = os.getenv("MODEL", "gpt-4o-mini")
AUTO_BUILD = os.getenv("AUTO_BUILD", "true").lower() in {"1", "true", "yes", "on"}
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "news_articles")

QA_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Answer based only on the provided context. "
     "If the answer is not in the context, say you don't know."),
    ("human", "Question: {question}\n\nContext:\n{context}")
])

# --- UI helpers ---------------------------------------------------------------

def banner() -> None:
    txt = Text()
    txt.append("News Search — LangChain + Chroma\n", style="bold")
    txt.append(f"Model: {MODEL}\n")
    txt.append(f"Collection: {CHROMA_COLLECTION}\n")
    txt.append(f"Persist dir: {CHROMA_DIR}\n")
    txt.append(f"AUTO_BUILD: {str(AUTO_BUILD).lower()}\n")
    console.print(Panel(txt, title="Startup", box=box.ROUNDED))
    console.print("Tips: try [cyan]/search central bank inflation[/cyan] or "
                  "[cyan]/ask \"What did BBC report today?\"[/cyan]\n")

def print_hits(hits: List[dict], elapsed: float | None = None) -> None:
    title = f"Top {len(hits)} results"
    if elapsed is not None:
        title += f"  (in {elapsed:.2f}s)"
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Title/Excerpt")
    table.add_column("URL", overflow="fold")
    table.add_column("Score", justify="right")
    for h in hits:
        source = f"{h.get('source','')}"
        text = (h.get("text") or "")[:200].replace("\n", " ")
        url = h.get("url", "")
        score = h.get("score")
        sc_str = f"{float(score):.4f}" if isinstance(score, (int, float)) else ""
        table.add_row(source, text, url, sc_str)
    console.print(table)

def rag_answer(db: PureChromaVectorDB, question: str, k: int = 5) -> tuple[str, List[dict], float, float]:
    t0 = time.time()
    hits = db.search(question, k=k)
    t_retrieval = time.time() - t0
    context = "\n\n".join([h["text"] for h in hits])

    t1 = time.time()
    llm = ChatOpenAI(model=MODEL, temperature=0.2)
    chain = QA_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context})
    t_generation = time.time() - t1
    return answer, hits, t_retrieval, t_generation

def pretty_stats(stats: dict, title: str = "Stats") -> None:
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    for k in ("collection", "persist_directory", "points_count"):
        if k in stats:
            table.add_row(k, str(stats[k]))
    console.print(table)

# --- Build helpers ------------------------------------------------------------

def build_and_report(db: PureChromaVectorDB) -> None:
    with console.status("[yellow]Building vectors from latest analysis file...[/yellow]", spinner="dots"):
        t0 = time.time()
        res = db.build()
        stats2 = db.stats()
        dt = time.time() - t0
    console.print(Panel.fit(
        f"[green]Build complete[/green] in {dt:.2f}s\n"
        f"Added: {res.get('count')} docs\n"
        f"Collection: {res.get('collection')}\n"
        f"Dir: {res.get('dir')}",
        title="Build", box=box.ROUNDED))
    pretty_stats(stats2, title="Post-build Stats")

def maybe_autobuild(db: PureChromaVectorDB) -> None:
    # Try stats; if it fails, attempt a build.
    try:
        stats = db.stats()
        points = int(stats.get("points_count", 0) or 0)
        if AUTO_BUILD and points == 0:
            console.print("[yellow]No vectors found.[/yellow] AUTO_BUILD is on.")
            build_and_report(db)
        else:
            console.print(f"[green]Vector store ready[/green] — "
                          f"collection: [bold]{stats.get('collection')}[/bold], "
                          f"points: [bold]{points}[/bold]")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not read stats ({e.__class__.__name__}: {e}). Attempting build...")
        try:
            build_and_report(db)
        except FileNotFoundError:
            console.print("[red]No analysis file found.[/red] Please run [cyan]python analysis.py[/cyan] first.")
            raise
        except Exception as e2:
            console.print(f"[red]Auto-build failed:[/red] {e2}")
            raise

# --- Main loop ----------------------------------------------------------------

def main() -> None:
    banner()
    db = PureChromaVectorDB()

    try:
        maybe_autobuild(db)
    except Exception:
        # Already printed a reason; exit gracefully to avoid a stuck REPL.
        return

    console.print("[bold]Interactive search. Type /help for commands.[/bold]")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            break

        if not raw:
            continue

        if raw.startswith("/help"):
            console.print("/search <text>   - semantic search")
            console.print('/ask "question"  - RAG-style Q&A')
            console.print("/stats           - vector DB stats")
            console.print("/rebuild         - rebuild vectors from latest analysis file")
            console.print("/quit            - exit")
            continue

        if raw.startswith("/quit"):
            console.print("Bye.")
            break

        if raw.startswith("/stats"):
            try:
                pretty_stats(db.stats())
            except Exception as e:
                console.print(f"[red]Stats error:[/red] {e}")
            continue

        if raw.startswith("/rebuild") or raw.startswith("/refresh"):
            try:
                build_and_report(db)
            except FileNotFoundError:
                console.print("[red]No analysis file found.[/red] Run [cyan]python analysis.py[/cyan] first.")
            except Exception as e:
                console.print(f"[red]Rebuild failed:[/red] {e}")
            continue

        if raw.startswith("/search"):
            q = raw[len("/search"):].strip()
            if not q:
                console.print("Usage: /search your query")
                continue
            try:
                t0 = time.time()
                hits = db.search(q, k=5)
                dt = time.time() - t0
                if not hits:
                    console.print(f"[yellow]No results[/yellow] (in {dt:.2f}s). "
                                  "You may need to /rebuild after running analysis.py.")
                else:
                    print_hits(hits, elapsed=dt)
            except Exception as e:
                console.print(f"[red]Search error:[/red] {e}")
            continue

        if raw.startswith("/ask"):
            try:
                parts = shlex.split(raw)
                question = " ".join(parts[1:])
            except Exception:
                question = raw[len("/ask"):].strip()
            if not question:
                console.print('Usage: /ask "your question"')
                continue
            try:
                answer, hits, t_ret, t_gen = rag_answer(db, question, k=5)
                console.print(Panel.fit(
                    f"[bold]Answer:[/bold]\n{answer}\n\n"
                    f"[dim]retrieval: {t_ret:.2f}s | generation: {t_gen:.2f}s | total: {t_ret + t_gen:.2f}s[/dim]",
                    title="Q&A", box=box.ROUNDED
                ))

                # Quick refs from top 3 hits
                if hits:
                    ref_table = Table(title="Context Sources", box=box.SIMPLE)
                    ref_table.add_column("#", justify="right", no_wrap=True)
                    ref_table.add_column("Source", style="cyan")
                    ref_table.add_column("URL", overflow="fold")
                    for i, h in enumerate(hits[:3], start=1):
                        ref_table.add_row(str(i), h.get("source", "") or "", h.get("url", "") or "")
                    console.print(ref_table)
            except Exception as e:
                console.print(f"[red]Q&A error:[/red] {e}")
            continue

        console.print("Unknown command. Try /help.")

if __name__ == "__main__":
    main()


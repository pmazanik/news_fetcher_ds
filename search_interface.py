#!/usr/bin/env python3
"""
search_interface.py
Interactive CLI on top of Qdrant + LangChain.

Commands:
  /search <query>
  /ask "<question>"
  /stats
  /help
  /quit
"""

from __future__ import annotations
import os
import shlex
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from langchain_openai import ChatOpenAI
from langchain.schema import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from vector_db import PureQdrantVectorDB

load_dotenv()

console = Console()
MODEL = os.getenv("MODEL", "gpt-4o-mini")

QA_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Answer based only on the provided context. "
     "If the answer is not in the context, say you don't know."),
    ("human", "Question: {question}\n\nContext:\n{context}")
])

def print_hits(hits: list[dict]) -> None:
    table = Table(title=f"Top {len(hits)} results")
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Title/Excerpt")
    table.add_column("URL", overflow="fold")
    for h in hits:
        source = f"{h.get('source','')}"
        text = (h.get("text") or "")[:200].replace("\n", " ")
        url = h.get("url", "")
        table.add_row(source, text, url)
    console.print(table)

def rag_answer(db: PureQdrantVectorDB, question: str, k: int = 5) -> str:
    hits = db.search(question, k=k)
    context = "\n\n".join([h["text"] for h in hits])
    llm = ChatOpenAI(model=MODEL, temperature=0.2)
    chain = QA_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context})
    return answer

def main() -> None:
    db = PureQdrantVectorDB()

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
            console.print("/search <text>  - semantic search")
            console.print('/ask "question" - RAG-style Q&A')
            console.print("/stats          - vector DB stats")
            console.print("/quit           - exit")
            continue

        if raw.startswith("/quit"):
            console.print("Bye.")
            break

        if raw.startswith("/stats"):
            console.print(db.stats())
            continue

        if raw.startswith("/search"):
            q = raw[len("/search"):].strip()
            if not q:
                console.print("Usage: /search your query")
                continue
            hits = db.search(q, k=5)
            print_hits(hits)
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
            answer = rag_answer(db, question, k=5)
            console.print(f"[bold]Answer:[/bold] {answer}")
            continue

        console.print("Unknown command. Try /help.")

if __name__ == "__main__":
    main()

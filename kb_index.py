"""
kb_index.py
───────────
Builds and queries a BM25 retrieval index over the product knowledge base.

BM25 is a proven, lightweight retrieval algorithm that works very well for
technical support text (error codes, product names, module names). It requires
no GPU, no torch, and no external APIs — only the pure-Python `rank-bm25`
package.

Strategy (matches DATA_SCHEMA.md recommendation):
  - Split each KB Markdown file on `---` (horizontal rules) → major sections
  - Store heading hierarchy and source file as metadata
  - Tokenise with simple whitespace + punctuation splitting (lower-case)
  - Index with BM25Okapi for fast top-k retrieval

The index is built once and cached in memory; subsequent calls reuse it.
"""

from __future__ import annotations

import re
import string
from pathlib import Path
from typing import List

from rank_bm25 import BM25Okapi

from config import KB_DIR, TOP_K_DOCS

# ── Module-level cache ────────────────────────────────────────────────────────
_bm25: BM25Okapi | None = None
_chunks: List[dict] = []   # {"text": ..., "source": ..., "heading": ...}


# ── Text helpers ──────────────────────────────────────────────────────────────

def _tokenise(text: str) -> List[str]:
    """
    Lowercase, remove punctuation except underscores (important for error codes
    like ERR_CONNECTION_TIMEOUT), split on whitespace.
    """
    text = text.lower()
    # Keep underscores and hyphens so error codes stay intact
    text = re.sub(r"[^\w\s\-_]", " ", text)
    return [t for t in text.split() if t]


def _split_markdown(text: str, source: str) -> List[dict]:
    """
    Split a Markdown file into sections at `---` horizontal rules.
    Preserves the last seen heading as metadata for each chunk.
    """
    sections = re.split(r"\n---\n", text)
    chunks = []
    last_heading = "Introduction"

    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading_match = re.search(r"^#{1,4}\s+(.+)", section, re.MULTILINE)
        if heading_match:
            last_heading = heading_match.group(1).strip()
        chunks.append({
            "text": section,
            "source": source,
            "heading": last_heading,
        })
    return chunks


# ── Index build ───────────────────────────────────────────────────────────────

def _build_index() -> None:
    global _bm25, _chunks

    all_chunks: List[dict] = []
    for md_path in sorted(KB_DIR.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        rel = str(md_path.relative_to(KB_DIR)).replace("\\", "/")
        all_chunks.extend(_split_markdown(text, rel))

    if not all_chunks:
        raise FileNotFoundError(f"No markdown files found under {KB_DIR}")

    tokenised = [_tokenise(c["text"]) for c in all_chunks]
    _bm25 = BM25Okapi(tokenised)
    _chunks = all_chunks


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = TOP_K_DOCS) -> List[dict]:
    """
    Retrieve the top-k most relevant KB chunks for a query.

    Returns a list of dicts: {text, source, heading, score}
    """
    global _bm25, _chunks

    if _bm25 is None:
        _build_index()

    tokens = _tokenise(query)
    scores = _bm25.get_scores(tokens)

    # Get top-k indices sorted by score descending
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        chunk = dict(_chunks[idx])
        chunk["score"] = float(scores[idx])
        results.append(chunk)

    return results


def format_for_prompt(chunks: List[dict]) -> str:
    """
    Format retrieved chunks into a compact string for the LLM prompt.
    Each chunk is truncated to avoid bloating the context window.
    """
    if not chunks:
        return "No relevant knowledge base articles found."

    MAX_CHARS_PER_CHUNK = 600
    lines = []
    for i, c in enumerate(chunks, 1):
        snippet = c["text"][:MAX_CHARS_PER_CHUNK].strip()
        if len(c["text"]) > MAX_CHARS_PER_CHUNK:
            snippet += " [...]"
        lines.append(
            f"[{i}] Source: {c['source']} | Section: {c['heading']}\n{snippet}"
        )
    return "\n\n".join(lines)

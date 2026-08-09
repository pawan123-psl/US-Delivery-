"""
triage.py
─────────
Core triage pipeline.

Public API:
  triage_ticket(ticket: TicketInput) -> TriageOutput

The pipeline:
  1. Retrieve relevant KB chunks (RAG)
  2. Build a structured prompt
  3. Call Groq LLM → parse JSON → validate with Pydantic
  4. Return a TriageOutput

Streaming variant:
  triage_ticket_stream(ticket: TicketInput) -> Generator[str, None, None]
  Yields raw text chunks from the LLM, then a final JSON sentinel.
"""

from __future__ import annotations

import json
import re
from typing import Generator

from groq import Groq

import config
import kb_index
from models import KBMatch, TicketInput, TriageOutput
from prompts import TRIAGE_PROMPT


# ── Groq client (module-level singleton) ──────────────────────────────────────

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not config.GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set."
            )
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


# ── JSON parsing helpers ──────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from LLM output.
    Handles cases where the model wraps the JSON in markdown fences despite
    instructions to the contrary.
    """
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{text}")
    return json.loads(match.group())


# ── Main triage function ──────────────────────────────────────────────────────

def triage_ticket(ticket: TicketInput) -> TriageOutput:
    """
    Run the full triage pipeline synchronously.

    Args:
        ticket: TicketInput with at minimum a `body` field.

    Returns:
        TriageOutput — fully structured triage result.
    """
    # 1. Retrieve relevant KB docs
    query = f"{ticket.subject} {ticket.body}"
    chunks = kb_index.retrieve(query)
    kb_context = kb_index.format_for_prompt(chunks)

    # 2. Build prompt
    prompt_text = TRIAGE_PROMPT["template"].format(
        subject=ticket.subject,
        body=ticket.body,
        kb_context=kb_context,
    )

    # 3. LLM call
    client = _get_client()
    completion = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise JSON-generating support triage assistant. "
                    "You ALWAYS return valid JSON with no extra text."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    raw = completion.choices[0].message.content

    # 4. Parse and validate
    data = _extract_json(raw)
    
    # Ensure kb_match is a nested dict (some models flatten it)
    if "kb_match" not in data:
        data["kb_match"] = {
            "found": False,
            "doc_title": None,
            "relevant_section": None,
            "confidence": "none",
        }

    output = TriageOutput(
        **data,
        ticket_id=ticket.ticket_id,
        prompt_version=TRIAGE_PROMPT["version"],
        retrieved_docs=[
            {"source": c["source"], "heading": c["heading"], "score": c["score"]}
            for c in chunks
        ],
    )
    return output


# ── Streaming variant ─────────────────────────────────────────────────────────

def triage_ticket_stream(ticket: TicketInput) -> Generator[str, None, TriageOutput]:
    """
    Stream LLM tokens as they arrive, then yield a final sentinel line.

    Yields:
        str — raw token chunks prefixed with "data: "
        Final yield: "data: [DONE]\\n" followed by the full JSON result

    Usage (SSE / Server-Sent Events):
        for chunk in triage_ticket_stream(ticket):
            print(chunk, end="", flush=True)
    """
    query = f"{ticket.subject} {ticket.body}"
    chunks = kb_index.retrieve(query)
    kb_context = kb_index.format_for_prompt(chunks)

    prompt_text = TRIAGE_PROMPT["template"].format(
        subject=ticket.subject,
        body=ticket.body,
        kb_context=kb_context,
    )

    client = _get_client()
    stream = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise JSON-generating support triage assistant. "
                    "You ALWAYS return valid JSON with no extra text."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
        stream=True,
    )

    full_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_text += delta
            yield f"data: {delta}"

    yield "data: [DONE]\n"

    # Parse and attach metadata
    data = _extract_json(full_text)
    if "kb_match" not in data:
        data["kb_match"] = {"found": False, "doc_title": None,
                            "relevant_section": None, "confidence": "none"}

    result = TriageOutput(
        **data,
        ticket_id=ticket.ticket_id,
        prompt_version=TRIAGE_PROMPT["version"],
        retrieved_docs=[
            {"source": c["source"], "heading": c["heading"], "score": c["score"]}
            for c in chunks
        ],
    )
    yield f"data: [RESULT] {result.model_dump_json()}\n"

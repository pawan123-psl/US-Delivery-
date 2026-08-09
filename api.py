"""
api.py
──────
FastAPI REST endpoints for:
  Task 1 — Ticket Triage pipeline
  Task 2 — TAM Account Health Summariser

Endpoints:
  POST /triage          — synchronous triage, returns JSON          (Task 1)
  POST /triage/stream   — streaming triage via Server-Sent Events   (Task 1)
  GET  /health          — liveness check
  GET  /brief/{account_id} — TAM account health brief               (Task 2)
  GET  /accounts           — list all account IDs and companies      (Task 2)

Run locally:
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from config import ACCOUNTS_PATH
from models import AccountBrief, TicketInput, TriageOutput
from triage import triage_ticket, triage_ticket_stream

app = FastAPI(
    title="Ticket Triage & TAM Brief Agent",
    description=(
        "Task 1: Intelligent ticket triage — classifies product area, issue category, "
        "urgency (P1–P4), surfaces KB articles, and drafts a first response. "
        "Task 2: TAM Account Health Summariser — generates a 3-section account brief "
        "with executive summary, risks, and recommended talking points."
    ),
    version="2.0.0",
)


@app.get("/health", summary="Health check")
def health() -> dict:
    return {"status": "ok", "service": "ticket-triage-agent"}


@app.post(
    "/triage",
    response_model=TriageOutput,
    summary="Triage a support ticket (synchronous)",
)
def triage_endpoint(ticket: TicketInput) -> TriageOutput:
    """
    Accept a raw support ticket (text or JSON with subject + body) and return
    a fully structured triage result.
    """
    try:
        return triage_ticket(ticket)
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Triage failed: {exc}") from exc


@app.post(
    "/triage/stream",
    summary="Triage a support ticket (streaming, SSE)",
)
def triage_stream_endpoint(ticket: TicketInput) -> StreamingResponse:
    """
    Same as /triage but streams LLM tokens via Server-Sent Events as they are
    generated. The final event is `data: [RESULT] {...json...}` containing the
    full structured output.
    """
    try:
        def event_generator():
            for chunk in triage_ticket_stream(ticket):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Streaming failed: {exc}") from exc


# ── Task 2 endpoints ──────────────────────────────────────────────────────────


@app.get(
    "/accounts",
    summary="List all accounts (Task 2)",
    tags=["Task 2 – TAM Brief"],
)
def list_accounts() -> list[dict]:
    """
    Task 2 — Return a lightweight list of all accounts (account_id + company name)
    for use in the UI dropdown.
    """
    try:
        raw = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
        return [
            {"account_id": a["account_id"], "company": a.get("company", "")}
            for a in raw
        ]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"accounts.json not found: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load accounts: {exc}") from exc


@app.get(
    "/brief/{account_id}",
    response_model=AccountBrief,
    summary="Generate TAM Account Health Brief (Task 2)",
    tags=["Task 2 – TAM Brief"],
)
def brief_endpoint(account_id: str) -> AccountBrief:
    """
    Task 2 — Accept an account_id, pull the relevant account summary and last 90 days
    of tickets from the mock dataset, and return a fully structured AccountBrief with:
      - executive_summary (3–5 sentences)
      - risks (flagged churn / escalation signals with direct ticket quotes)
      - talking_points (recommended TAM talking points)

    Output is deterministic for the same input (temperature=0.0).
    """
    from account_brief import generate_brief  # Task 2 — lazy import to keep startup clean

    try:
        return generate_brief(account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {exc}") from exc

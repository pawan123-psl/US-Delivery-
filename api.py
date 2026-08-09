"""
api.py
──────
FastAPI REST endpoint for the triage pipeline.

Endpoints:
  POST /triage          — synchronous triage, returns JSON
  POST /triage/stream   — streaming triage via Server-Sent Events
  GET  /health          — liveness check

Run locally:
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from models import TicketInput, TriageOutput
from triage import triage_ticket, triage_ticket_stream

app = FastAPI(
    title="Ticket Triage Agent",
    description=(
        "Intelligent ticket triage: classifies product area, issue category, "
        "urgency (P1–P4), surfaces KB articles, and drafts a first response."
    ),
    version="1.0.0",
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

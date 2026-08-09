"""
models.py
─────────
Pydantic models for structured input and output of the triage pipeline.
Using Pydantic v2 throughout.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Input ─────────────────────────────────────────────────────────────────────

class TicketInput(BaseModel):
    """
    Incoming ticket. Accepts either:
      - plain text in `body` (with optional `subject`), or
      - a full JSON ticket from the dataset
    """
    subject: str = Field(default="(no subject)", description="Ticket subject line")
    body: str = Field(..., description="Full ticket body text")
    ticket_id: Optional[str] = Field(default=None, description="Optional ticket ID for reference")
    account_id: Optional[str] = Field(default=None, description="Optional account ID for context")
    plan_tier: Optional[str] = Field(default=None, description="Customer plan tier if known")


# ── Output ────────────────────────────────────────────────────────────────────

class KBMatch(BaseModel):
    found: bool
    doc_title: Optional[str] = None
    relevant_section: Optional[str] = None
    confidence: Literal["high", "medium", "low", "none"] = "none"


class TriageOutput(BaseModel):
    """Structured triage result returned by the pipeline."""

    # Core classifications
    product_area: str = Field(description="Product name and module")
    issue_category: Literal[
        "Bug", "Feature Request", "How-To", "Performance",
        "Billing", "Integration", "Onboarding", "Data Loss"
    ]
    urgency: Literal["P1", "P2", "P3", "P4"]
    urgency_reasoning: str

    # Knowledge base
    kb_match: KBMatch

    # Routing
    responder_team: Literal[
        "Tier-1 Support", "Tier-2 Engineering", "Billing & Accounts",
        "Onboarding", "Security", "TAM Escalation"
    ]
    responder_reasoning: str

    # Draft response
    draft_response: str

    # Metadata (added by pipeline, not LLM)
    ticket_id: Optional[str] = None
    prompt_version: Optional[str] = None
    retrieved_docs: Optional[list] = None

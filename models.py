"""
models.py
─────────
Pydantic models for structured input and output of the triage pipeline (Task 1)
and the TAM Account Health Summariser (Task 2).
Using Pydantic v2 throughout.
"""

from __future__ import annotations

from typing import List, Literal, Optional
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


# ── Task 2 Models ─────────────────────────────────────────────────────────────
# Models for the TAM Account Health Summariser (Task 2).
# These are appended below the existing Task 1 models and do not modify them.


class RiskItem(BaseModel):
    """
    A single flagged risk or churn/escalation signal identified in the account's
    recent tickets.

    Fields:
      description  : Human-readable summary of the risk.
      ticket_id    : The source ticket ID (optional — may be None for account-level risks).
      ticket_quote : A direct verbatim excerpt from the ticket body that justifies the flag.
    """
    description: str = Field(description="Short description of the risk or escalation signal")
    ticket_id: Optional[str] = Field(default=None, description="Source ticket ID, if applicable")
    ticket_quote: str = Field(description="Direct verbatim quote from the ticket body that justifies this flag")


class AccountBrief(BaseModel):
    """
    Full TAM Account Health Brief produced by Task 2 pipeline.

    Contains:
      - Account metadata (from accounts.json)
      - executive_summary : 3–5 sentence overall health narrative
      - risks             : list of flagged churn/escalation risks with ticket quotes
      - talking_points    : recommended TAM talking points for the next call
      - tickets_analysed  : how many tickets were included in the analysis
      - generated_at      : ISO-8601 timestamp of generation (UTC)
    """
    # ── Account metadata ──────────────────────────────────────────────────────
    account_id: str = Field(description="Unique account identifier, e.g. ACC-3336")
    company: str = Field(description="Company / organisation name")
    tam: str = Field(description="Assigned Technical Account Manager name")
    plan_tier: str = Field(description="Subscription plan tier, e.g. Enterprise")
    health_status: str = Field(description="Current health label from the account record")
    arr_usd: Optional[float] = Field(default=None, description="Annual Recurring Revenue in USD")

    # ── LLM-generated sections ────────────────────────────────────────────────
    executive_summary: str = Field(
        description="3–5 sentence executive summary of the account's current health"
    )
    risks: List[RiskItem] = Field(
        default_factory=list,
        description="Flagged churn risks and escalation signals, each with a direct ticket quote",
    )
    talking_points: List[str] = Field(
        default_factory=list,
        description="Recommended talking points for the TAM's next account call",
    )

    # ── Pipeline metadata ─────────────────────────────────────────────────────
    tickets_analysed: int = Field(description="Number of tickets included in this analysis")
    generated_at: str = Field(description="UTC timestamp of generation in ISO-8601 format")

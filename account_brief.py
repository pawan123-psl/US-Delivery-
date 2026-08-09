"""
account_brief.py  — Task 2
──────────────────────────
TAM Account Health Summariser pipeline.

Public API:
  generate_brief(account_id: str) -> AccountBrief

Pipeline (Task 2):
  1. Load accounts.json → find the target account (graceful 404 if missing)
  2. Load tickets.json  → filter to this account_id, last 90 days
  3. Format a structured prompt with account metadata + ticket summaries
  4. Call Groq LLM at temperature=0.0 (deterministic)
  5. Parse JSON response → validate with AccountBrief Pydantic model
  6. Return AccountBrief with metadata attached

Run directly (CLI wrapper is run_brief.py):
  python -c "from account_brief import generate_brief; print(generate_brief('ACC-3336'))"
"""

from __future__ import annotations

# Task 2 — standard library imports
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

# Task 2 — project imports
from groq import Groq

import config
from models import AccountBrief, RiskItem       # Task 2 models
from prompts import TAM_BRIEF_PROMPT             # Task 2 prompt


# ── Task 2: Groq client (module-level singleton, same pattern as triage.py) ───

_client: Optional[Groq] = None


def _get_client() -> Groq:
    """Return a cached Groq client, initialising it on first call."""
    global _client
    if _client is None:
        if not config.GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


# ── Task 2: Data loading helpers ──────────────────────────────────────────────

def _load_accounts() -> list[dict]:
    """Load and return all accounts from ACCOUNTS_PATH."""
    path = config.ACCOUNTS_PATH
    if not path.exists():
        raise FileNotFoundError(f"accounts.json not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tickets() -> list[dict]:
    """Load and return all tickets from TICKETS_PATH."""
    path = config.TICKETS_PATH
    if not path.exists():
        raise FileNotFoundError(f"tickets.json not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _find_account(account_id: str, accounts: list[dict]) -> Optional[dict]:
    """
    Task 2 — Return the account dict matching account_id, or None if not found.
    Case-insensitive match for robustness.
    """
    needle = account_id.strip().upper()
    for acct in accounts:
        if acct.get("account_id", "").upper() == needle:
            return acct
    return None


def _filter_tickets_last_90d(account_id: str, tickets: list[dict]) -> list[dict]:
    """
    Task 2 — Return tickets for the given account_id created within the last 90 days.

    Note: tickets may reference an account_id that does not appear in accounts.json —
    that is handled upstream (we still analyse the tickets even without account metadata).
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=90)
    result = []
    needle = account_id.strip().upper()
    for t in tickets:
        if t.get("account_id", "").upper() != needle:
            continue
        created_raw = t.get("created_at", "")
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # If we can't parse the date, include the ticket to be safe
            result.append(t)
            continue
        if created >= cutoff:
            result.append(t)
    return result


# ── Task 2: Prompt formatting ─────────────────────────────────────────────────

def _format_ticket_summaries(tickets: list[dict]) -> str:
    """
    Task 2 — Format the list of recent tickets into a readable block for the prompt.
    Each ticket shows its ID, subject, urgency, status, and full body.
    """
    if not tickets:
        return "(No tickets in the last 90 days)"

    parts = []
    for t in tickets:
        parts.append(
            f"--- Ticket {t.get('ticket_id', 'N/A')} ---\n"
            f"Subject  : {t.get('subject', '')}\n"
            f"Urgency  : {t.get('urgency', 'N/A')}  |  Status: {t.get('status', 'N/A')}\n"
            f"Product  : {t.get('product', 'N/A')} / {t.get('product_area', 'N/A')}\n"
            f"Created  : {t.get('created_at', 'N/A')}\n"
            f"Body:\n{t.get('body', '').strip()}\n"
        )
    return "\n".join(parts)


# ── Task 2: JSON parsing helper (same pattern as triage.py) ──────────────────

def _extract_json(text: str) -> dict:
    """
    Task 2 — Robustly extract a JSON object from LLM output.
    Strips markdown fences and finds the first {...} block.
    """
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{text}")
    return json.loads(match.group())


# ── Task 2: Main pipeline ─────────────────────────────────────────────────────

def generate_brief(account_id: str) -> AccountBrief:
    """
    Task 2 — Generate a TAM Account Health Brief for the given account_id.

    Args:
        account_id: The account identifier to look up (e.g. "ACC-3336").

    Returns:
        AccountBrief — fully structured brief with 3 sections + metadata.

    Raises:
        ValueError      : If account_id is not found in accounts.json AND has no
                          recent tickets (nothing to analyse).
        EnvironmentError: If GROQ_API_KEY is missing.
        FileNotFoundError: If data files are missing.
    """
    # ── 1. Load data ──────────────────────────────────────────────────────────
    all_accounts = _load_accounts()
    all_tickets = _load_tickets()

    account = _find_account(account_id, all_accounts)
    recent_tickets = _filter_tickets_last_90d(account_id, all_tickets)

    # Task 2 — graceful handling: account not in accounts.json
    if account is None and not recent_tickets:
        raise ValueError(
            f"Account '{account_id}' not found in accounts.json and has no recent tickets. "
            "Please verify the account ID."
        )

    # Task 2 — build a synthetic account dict if only tickets are available
    if account is None:
        # Derive what we can from the ticket data
        sample = recent_tickets[0] if recent_tickets else {}
        account = {
            "account_id": account_id,
            "company": sample.get("company", "Unknown"),
            "tam": "Unknown",
            "plan_tier": sample.get("plan_tier", "Unknown"),
            "health_status": "Unknown",
            "arr_usd": None,
            "seats_licensed": None,
            "seats_active": None,
            "products": [],
            "open_tickets": len(recent_tickets),
            "p1_tickets_last_30d": sum(
                1 for t in recent_tickets if t.get("urgency") == "P1"
            ),
            "renewal_date": "Unknown",
            "last_qbr_date": "Unknown",
            "primary_contact": {"name": "Unknown", "title": "Unknown"},
            "escalation_notes": [],
        }

    # ── 2. Format prompt ──────────────────────────────────────────────────────
    ticket_summaries = _format_ticket_summaries(recent_tickets)
    primary_contact = account.get("primary_contact", {})

    prompt_text = TAM_BRIEF_PROMPT["template"].format(
        account_id=account.get("account_id", account_id),
        company=account.get("company", "Unknown"),
        tam=account.get("tam", "Unknown"),
        plan_tier=account.get("plan_tier", "Unknown"),
        health_status=account.get("health_status", "Unknown"),
        arr_usd=f"${account.get('arr_usd', 0):,.0f}" if account.get("arr_usd") else "Unknown",
        products=", ".join(account.get("products", [])) or "Unknown",
        seats_licensed=account.get("seats_licensed", "Unknown"),
        seats_active=account.get("seats_active", "Unknown"),
        open_tickets=account.get("open_tickets", len(recent_tickets)),
        p1_tickets_last_30d=account.get("p1_tickets_last_30d", 0),
        renewal_date=account.get("renewal_date", "Unknown"),
        last_qbr_date=account.get("last_qbr_date", "Unknown"),
        primary_contact_name=primary_contact.get("name", "Unknown"),
        primary_contact_title=primary_contact.get("title", "Unknown"),
        escalation_notes="; ".join(account.get("escalation_notes", [])) or "None",
        ticket_count=len(recent_tickets),
        ticket_summaries=ticket_summaries,
    )

    # ── 3. LLM call (temperature=0.0 for determinism — Task 2 requirement) ───
    client = _get_client()
    completion = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise JSON-generating TAM assistant. "
                    "You ALWAYS return valid JSON with no extra text."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        temperature=0.0,                   # Task 2: deterministic output required
        max_tokens=config.LLM_MAX_TOKENS,
    )

    raw = completion.choices[0].message.content

    # ── 4. Parse and validate ─────────────────────────────────────────────────
    data = _extract_json(raw)

    # Task 2 — normalise risks: convert raw dicts to RiskItem objects
    raw_risks = data.get("risks", [])
    risks = []
    for r in raw_risks:
        if isinstance(r, dict):
            risks.append(RiskItem(
                description=r.get("description", ""),
                ticket_id=r.get("ticket_id") or None,
                ticket_quote=r.get("ticket_quote", ""),
            ))

    # ── 5. Assemble AccountBrief ──────────────────────────────────────────────
    brief = AccountBrief(
        account_id=account.get("account_id", account_id),
        company=account.get("company", "Unknown"),
        tam=account.get("tam", "Unknown"),
        plan_tier=account.get("plan_tier", "Unknown"),
        health_status=account.get("health_status", "Unknown"),
        arr_usd=account.get("arr_usd"),
        executive_summary=data.get("executive_summary", ""),
        risks=risks,
        talking_points=data.get("talking_points", []),
        tickets_analysed=len(recent_tickets),
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
    )
    return brief

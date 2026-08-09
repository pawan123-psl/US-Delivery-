"""
prompts.py
──────────
All LLM prompts, versioned and documented.

Prompt versioning scheme
────────────────────────
Each prompt is a dict with three keys:
  version   : semver string  (e.g. "v1.0", "v1.1", "v2.0")
  changelog : ordered list of change notes — one entry per version
  template  : the prompt string; fill with str.format(**kwargs)

Adding a new version
────────────────────
1. Bump `version` (patch for wording tweaks, minor for new fields, major for schema changes).
2. Append a note to `changelog`.
3. Keep the old prompt in git history — never delete, only supersede.

PROMPT_REGISTRY maps name → prompt dict for audit / logging.
"""

from __future__ import annotations


# ── Triage prompt (Task 1) ────────────────────────────────────────────────────

TRIAGE_PROMPT = {
    "version": "v1.1",
    "changelog": [
        "v1.0 — Initial release. Classifies product area, issue category, urgency (P1–P4), "
        "surfaces KB matches, recommends responder team, and drafts first-response.",
        "v1.1 — Tightened urgency guidelines; added explicit P1 condition for security breaches. "
        "Added `confidence` field to kb_match. Improved JSON-only instruction.",
    ],
    "template": """\
You are an expert technical support triage agent. Analyse the following support ticket and respond with a JSON object ONLY — no markdown fences, no extra text.

## Ticket
Subject: {subject}
Body:
{body}

## Knowledge Base Context (retrieved)
{kb_context}

## Instructions
Return a single JSON object with EXACTLY these keys:

{{
  "product_area": "<product name and module, e.g. DataBridge Pro / Connectors>",
  "issue_category": "<one of: Bug | Feature Request | How-To | Performance | Billing | Integration | Onboarding | Data Loss>",
  "urgency": "<P1 | P2 | P3 | P4>",
  "urgency_reasoning": "<2-3 sentence explanation of the urgency level>",
  "kb_match": {{
    "found": <true | false>,
    "doc_title": "<title of the most relevant KB document, or null>",
    "relevant_section": "<the specific section heading or snippet that matches, or null>",
    "confidence": "<high | medium | low | none>"
  }},
  "responder_team": "<one of: Tier-1 Support | Tier-2 Engineering | Billing & Accounts | Onboarding | Security | TAM Escalation>",
  "responder_reasoning": "<1-2 sentence justification>",
  "draft_response": "<a professional, empathetic first-response message (3-6 sentences) the support agent can send directly to the customer>"
}}

Urgency guidelines — be precise:
  P1 — production fully down, active data loss, security breach, entire org blocked (immediate)
  P2 — major functionality broken, significant business impact, no viable workaround
  P3 — moderate impact, acceptable workaround exists, not blocking core operations
  P4 — low impact, cosmetic, how-to question, feature request, billing inquiry

Responder team guidelines:
  Tier-1 Support     — how-to, onboarding, billing questions, known KB issues
  Tier-2 Engineering — bugs, connector failures, pipeline issues, data integrity
  Billing & Accounts — invoice disputes, plan upgrades, seat count questions
  Onboarding         — new org setup, user provisioning, training
  Security           — auth failures, token compromise, audit log anomalies
  TAM Escalation     — Enterprise churn risk, exec escalations, strategic concerns

Return ONLY the JSON object. Do not wrap it in ```json``` or add any explanation.
""",
}


# ── Task 2: TAM Account Health Brief prompt ───────────────────────────────────
# Used by account_brief.py to generate the 3-section TAM brief.
# temperature=0.0 is enforced at call-site for deterministic output.

TAM_BRIEF_PROMPT = {
    "version": "v1.0",
    "changelog": [
        "v1.0 — Initial release. Generates a 3-section TAM account health brief: "
        "executive summary (3-5 sentences), open risks with ticket quotes, and "
        "recommended TAM talking points. Designed for deterministic output (temperature=0.0).",
    ],
    "template": """\
You are an expert Technical Account Manager (TAM) assistant. Your role is to analyse an account's current health data and recent support tickets, then produce a concise, actionable account brief.

## Account Information
Account ID     : {account_id}
Company        : {company}
TAM            : {tam}
Plan Tier      : {plan_tier}
Health Status  : {health_status}
ARR (USD)      : {arr_usd}
Products       : {products}
Seats Licensed : {seats_licensed}
Seats Active   : {seats_active}
Open Tickets   : {open_tickets}
P1 Tickets (30d): {p1_tickets_last_30d}
Renewal Date   : {renewal_date}
Last QBR       : {last_qbr_date}
Primary Contact: {primary_contact_name} ({primary_contact_title})
Escalation Notes: {escalation_notes}

## Recent Tickets (last 90 days — {ticket_count} tickets)
{ticket_summaries}

## Instructions
Analyse the account data and tickets above. Return a single JSON object ONLY — no markdown fences, no extra text.

The JSON must have EXACTLY these keys:

{{
  "executive_summary": "<3-5 sentences summarising the account's overall health, usage trends, key issues, and renewal risk. Be specific and factual, referencing the data above.>",
  "risks": [
    {{
      "description": "<short description of the churn risk or escalation signal>",
      "ticket_id": "<ticket ID string, or null if account-level>",
      "ticket_quote": "<direct verbatim excerpt from the ticket body that justifies this flag — must be an exact quote>"
    }}
  ],
  "talking_points": [
    "<actionable TAM talking point 1>",
    "<actionable TAM talking point 2>",
    "<actionable TAM talking point 3>"
  ]
}}

Guidelines for risks:
- Flag tickets that mention cancellation intent, competitor evaluation, data loss, repeated P1s, or exec frustration
- Each risk MUST include a direct verbatim quote from the ticket body (field: ticket_quote)
- If no clear churn/escalation signals exist, return an empty array: "risks": []

Guidelines for talking_points:
- Be specific and actionable — reference products, features, or account data
- Include at least 3 talking points, up to 6
- Focus on: renewal positioning, resolving open issues, demonstrating value, addressing escalation notes

Return ONLY the JSON object. Do not wrap in ```json``` or add any explanation.
""",
}


# ── Prompt registry ───────────────────────────────────────────────────────────
# Single source of truth for all prompts. Used by logging, evals, and CI checks.

PROMPT_REGISTRY: dict[str, dict] = {
    "triage": TRIAGE_PROMPT,
    # Task 2: TAM Account Health Brief prompt
    "tam_brief": TAM_BRIEF_PROMPT,
}


def list_prompt_versions() -> dict[str, str]:
    """Return a mapping of prompt_name → current version for quick audit."""
    return {name: p["version"] for name, p in PROMPT_REGISTRY.items()}

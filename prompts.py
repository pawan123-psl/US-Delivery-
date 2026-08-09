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


# ── Prompt registry ───────────────────────────────────────────────────────────
# Single source of truth for all prompts. Used by logging, evals, and CI checks.

PROMPT_REGISTRY: dict[str, dict] = {
    "triage": TRIAGE_PROMPT,
}


def list_prompt_versions() -> dict[str, str]:
    """Return a mapping of prompt_name → current version for quick audit."""
    return {name: p["version"] for name, p in PROMPT_REGISTRY.items()}

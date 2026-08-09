# Production-Grade AI for Technical Support & TAM Teams

A two-task AI system built for internal tooling teams at a B2B SaaS company. It combines intelligent ticket triage with automated account health summarisation — replacing hours of manual work with sub-2-second LLM-powered results.

---

## What This Solves

| Problem | Solution |
|---|---|
| Support agents manually classifying hundreds of tickets a day | Task 1 — auto-classifies product area, urgency, category, routes to the right team, and drafts the first response |
| TAMs spending 30+ minutes before each QBR piecing together account context | Task 2 — generates a complete 3-section brief from raw account + ticket data in seconds |

---

## Live Demo

```bash
# UI — all three tasks in one interface
streamlit run app.py
```

Opens at `http://localhost:8501` with three tabs:
- **🎫 Ticket Triage** — paste any ticket, get instant structured triage
- **📋 TAM Account Brief** — pick an account, get a full QBR-ready brief
- **📊 Evaluation Harness** — run Task 3 eval directly from the browser, download reports

---

## Architecture

### Task 1 — Ticket Triage Pipeline

```
Raw ticket (text or JSON)
        │
        ▼
  ┌─────────────┐   BM25 search (rank-bm25)   ┌──────────────────────────┐
  │  kb_index   │◄──────────────────────────►│  9 KB Markdown docs       │
  │  (RAG layer)│   top-3 relevant chunks     │  ~30 sections total       │
  └─────┬───────┘                             └──────────────────────────┘
        │ formatted KB context
        ▼
  ┌───────────────────────────────────────┐
  │  triage.py  (TRIAGE_PROMPT v1.1)      │ ──► Groq LLM (llama-3.3-70b)
  │  prompt template + KB chunks          │ ◄── structured JSON response
  └─────┬─────────────────────────────────┘
        │ parsed + validated by Pydantic
        ▼
  TriageOutput: product_area · issue_category · urgency (P1–P4)
              · urgency_reasoning · kb_match · responder_team
              · responder_reasoning · draft_response · prompt_version
        │
        ▼
  CLI (run_triage.py) / REST API (api.py) / Streamlit UI (app.py)
```

### Task 2 — TAM Account Brief Pipeline

```
account_id
        │
        ▼
  ┌──────────────────────────────────────┐
  │  account_brief.py                    │
  │  1. Load accounts.json → find account│
  │  2. Load tickets.json → filter 90d   │
  │  3. Format structured prompt         │
  └──────────┬───────────────────────────┘
             │ account metadata + ticket summaries
             ▼
  ┌───────────────────────────────────────┐
  │  TAM_BRIEF_PROMPT v1.0                │ ──► Groq LLM (temperature=0.0)
  │  Account + ticket context             │ ◄── deterministic JSON response
  └─────┬─────────────────────────────────┘
        │ parsed + validated by Pydantic
        ▼
  AccountBrief: executive_summary (3–5 sentences)
              · risks (with direct ticket quotes)
              · talking_points
              · metadata (tickets_analysed, generated_at)
        │
        ▼
  CLI (run_brief.py) / REST API (/brief/{account_id}) / Streamlit Tab 2
```

---

## Setup

### 1. Install dependencies

```bash
cd Task-1
pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` and set your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATA_DIR=../Task/resources/starter-repo
```

Get a **free** Groq API key at [console.groq.com](https://console.groq.com) — no credit card required.

### 3. Verify everything loads

```bash
python -c "import triage; import account_brief; import api; from models import AccountBrief, RiskItem, TriageOutput; print('ALL OK')"
```

Expected output: `ALL OK`

---

## Task 1 — Intelligent Ticket Triage

### What it produces

For any incoming support ticket (free text or JSON), the pipeline outputs:

| Field | Description |
|---|---|
| `product_area` | Product name and module, e.g. `DataBridge Pro / Connectors` |
| `issue_category` | Bug · Feature Request · How-To · Performance · Billing · Integration · Onboarding · Data Loss |
| `urgency` | P1 (critical) → P4 (low) with reasoning |
| `kb_match` | Matched KB article title, section, and confidence (high/medium/low) |
| `responder_team` | Tier-1 Support · Tier-2 Engineering · Billing & Accounts · Onboarding · Security · TAM Escalation |
| `draft_response` | Professional first-response message ready to send |
| `prompt_version` | Prompt version used (for auditability) |

### CLI usage

```bash
# Triage a ticket from the dataset by ID
python run_triage.py --ticket-id TKT-10000

# Triage free-text input
python run_triage.py --subject "Pipeline stopped" --body "ERR_CONNECTION_TIMEOUT on DataBridge Pro. 47 engineers blocked."

# Stream tokens as they generate
python run_triage.py --ticket-id TKT-10003 --stream

# Raw JSON output
python run_triage.py --ticket-id TKT-10000 --json
```

### Sample output

```
──────────────────────────────────────────────────────────────
  Ticket ID    : TKT-10000
  Product Area : DataBridge Pro / Data Ingestion
  Category     : Feature Request
  Urgency      : P2  (Bulk operations unavailable at scale — 116 users impacted,
                       no viable one-by-one workaround for production use)
  Responder    : Tier-1 Support
  Reason       : Known feature gap with a documented workaround available.

  KB Match     : ✅  DataBridge Pro — Product Reference [high]
  Section      : Data Ingestion

  Draft Response:
    Thank you for reaching out. I understand that the lack of bulk archive
    operations in the Data Ingestion module is significantly impacting your
    team's productivity at scale. While native bulk operations are not yet
    available, I can walk you through the API-based batch approach that some
    teams use as a workaround ...

  Prompt version: v1.1
──────────────────────────────────────────────────────────────
```

### REST API

```bash
# Start the server
uvicorn api:app --reload --port 8000

# Triage a ticket (synchronous)
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "Pipeline down", "body": "ERR_CONNECTION_TIMEOUT on DataBridge Pro."}'

# Streaming triage (Server-Sent Events)
curl -N -X POST http://localhost:8000/triage/stream \
  -H "Content-Type: application/json" \
  -d '{"subject": "Pipeline down", "body": "ERR_CONNECTION_TIMEOUT after 30s."}'

# Health check
curl http://localhost:8000/health
```

Interactive Swagger docs: `http://localhost:8000/docs`

---

## Task 2 — TAM Account Health Summariser

### What it produces

For any `account_id`, the pipeline pulls 90 days of ticket history and generates a 3-section brief:

**Section 1 — Executive Summary**
3–5 sentences covering overall health, usage trends, key open issues, and renewal risk. Factual and data-referenced.

**Section 2 — Open Risks & Flagged Issues**
Each risk includes:
- A description of the churn signal or escalation trigger
- The source ticket ID
- A **direct verbatim quote** from the ticket body that justifies the flag

**Section 3 — Recommended Talking Points**
3–6 specific, actionable talking points for the TAM's next account call. References actual products, usage data, and open issues.

Output is **deterministic** — `temperature=0.0` ensures the same input always produces the same output.

### CLI usage

```bash
# Generate a TAM brief
python run_brief.py --account-id ACC-3336

# Raw JSON output
python run_brief.py --account-id ACC-3336 --json

# Try an at-risk account
python run_brief.py --account-id ACC-8113
```

### Sample output

```
══════════════════════════════════════════════════════════════════════
  TAM ACCOUNT HEALTH BRIEF  —  Task 2
══════════════════════════════════════════════════════════════════════
  Account   : ACC-3336  |  Omni Consumer Products
  TAM       : Rohan Mehta
  Plan      : Business  |  Health: At Risk
  ARR       : $500,000
  Tickets   : 4 analysed (last 90 days)
══════════════════════════════════════════════════════════════════════

📋  EXECUTIVE SUMMARY
──────────────────────────────────────────────────────────────────────
Omni Consumer Products is a high-value Business plan account ($500k ARR)
currently flagged as At Risk with an Inactive usage trend. The account has
7 open tickets and the primary decision maker has been noted as evaluating
competing vendors. Renewal is scheduled for August 2026 — urgent intervention
is recommended.

⚠️   OPEN RISKS & FLAGGED ISSUES
──────────────────────────────────────────────────────────────────────
  1. [TKT-10XXX] Decision maker considering vendor switch
     Quote: "our management team has started evaluating alternative platforms"

  2. [TKT-10XXX] Usage has gone inactive despite large licensed seat base
     Quote: "we haven't been using the platform for the past few weeks"

💬  RECOMMENDED TALKING POINTS
──────────────────────────────────────────────────────────────────────
  1. Address competitor evaluation directly — schedule an executive sponsor call
  2. Review WorkflowEngine and AnalyticsHub adoption blockers with the IT team
  3. Offer a health-check session to clear all 7 open tickets before renewal
══════════════════════════════════════════════════════════════════════
```

### REST API

```bash
# List all accounts (for UI or integration)
curl http://localhost:8000/accounts

# Generate an account brief
curl http://localhost:8000/brief/ACC-3336

# Another example — at-risk account
curl http://localhost:8000/brief/ACC-8113
```

---

## File Structure

```
Task-1/
│
│  ── Core shared modules ──────────────────────────────────────────
├── config.py          # All settings loaded from .env (LLM, RAG, data paths)
├── models.py          # Pydantic schemas for Task 1 (TriageOutput) and Task 2 (AccountBrief)
├── prompts.py         # Versioned prompts — PROMPT_REGISTRY with version + changelog
│
│  ── Task 1: Ticket Triage ────────────────────────────────────────
├── kb_index.py        # BM25 RAG index over 9 KB markdown files (~30 chunks)
├── triage.py          # Core pipeline: triage_ticket() + triage_ticket_stream()
├── run_triage.py      # CLI entry point for Task 1
│
│  ── Task 2: TAM Account Brief ────────────────────────────────────
├── account_brief.py   # Core pipeline: generate_brief(account_id) -> AccountBrief
├── run_brief.py       # CLI entry point for Task 2
│
│  ── Shared API & UI ───────────────────────────────────────────────
├── api.py             # FastAPI: /triage · /triage/stream · /brief/{id} · /accounts · /health
├── app.py             # Streamlit UI: Tab 1 (Triage) + Tab 2 (TAM Brief) + Tab 3 (Eval)
│
│  ── Task 3: Evaluation Harness ───────────────────────────────────
├── eval_harness.py    # 12 test cases (6 per task), rule-based + LLM-as-judge scoring
│                      # Outputs eval_report.json + eval_report.md
│
├── .github/
│   └── workflows/
│       └── eval.yml   # GitHub Actions CI — smoke tests on every push/PR
├── requirements.txt
├── .env.example       # Required env vars template (never commit .env)
└── README.md
```

---

## Bonus Features

| Bonus | Marks | Status | Implementation |
|---|---|---|---|
| Streamlit UI | +5 | ✅ | `app.py` — three-tab UI: Ticket Triage, TAM Brief, Evaluation Harness |
| Streaming output | +3 | ✅ | `triage_ticket_stream()` in `triage.py`; SSE endpoint `POST /triage/stream`; `--stream` CLI flag |
| GitHub Actions CI | +2 | ✅ | `.github/workflows/eval.yml` — runs on every push and PR |
| Prompt versioning | +2 | ✅ | `PROMPT_REGISTRY` in `prompts.py` — every prompt has `version` + `changelog`; version echoed in every output |

---

## Key Design Decisions

### BM25 over vector embeddings (Task 1 RAG)

Technical support text is keyword-dense — error codes like `ERR_CONNECTION_TIMEOUT`, product names, module names. BM25 (`rank-bm25`) retrieves the exact error reference reliably without a GPU, without an embeddings API call, and with near-zero latency. For a production KB with thousands of documents, a hybrid BM25 + dense retrieval approach would be the right evolution.

### Groq + llama-3.3-70b

Free tier, ~1–2s end-to-end latency, reliable structured JSON output from the 70B model. `temperature=0.0` across both tasks ensures deterministic outputs for the same input — a Task 2 explicit requirement and good practice for Task 1 consistency.

### Pydantic v2 validation as a hard gate

LLM responses are parsed and validated against typed Pydantic models (`TriageOutput`, `AccountBrief`). If the model returns an invalid urgency value, missing required field, or malformed JSON, the pipeline fails loudly with a clear error — no silent bad data passed downstream.

### Prompt versioning

Every prompt in `PROMPT_REGISTRY` carries a `version` string and ordered `changelog` list. The version is echoed in every `TriageOutput` response. This enables regression tracking, A/B testing, and audit trails — critical for production AI systems.

### Graceful data gaps (Task 2)

The task spec notes that not every `account_id` in `tickets.json` has a matching record in `accounts.json`. The pipeline handles this by synthesising a minimal account context from available ticket data rather than hard-failing — a more realistic production behaviour.

---

## Design Note (Task 4)

### Failure Modes

**1. LLM returns invalid or partial JSON**
The model occasionally wraps output in markdown fences or omits required fields despite prompt instructions. The `_extract_json()` helper strips fences and uses regex to find the first `{...}` block. Pydantic then validates all fields. In production, a retry with a simplified prompt would be the mitigation.

**2. KB retrieval misses the relevant article**
BM25 can fail on paraphrased queries where the customer describes an error in different words than the KB uses. Detection: log retrieval scores; if all scores are below a threshold, flag low confidence. Mitigation: hybrid BM25 + semantic search; expand KB coverage; add synonym mapping for common error codes.

**3. Stale account data producing incorrect briefs (Task 2)**
`accounts.json` is a point-in-time snapshot. If a TAM uses a brief generated 2 weeks ago, the risk signals may be outdated. Detection: include `generated_at` timestamp in every output (already implemented). Mitigation: set a TTL on cached briefs; force regeneration before QBRs.

### Latency vs Quality Trade-off

`TOP_K_DOCS=3` (retrieving 3 KB chunks) was chosen to balance prompt length against retrieval breadth. Increasing to 5–7 chunks would improve recall on multi-product tickets but adds ~400 tokens to the prompt and increases latency by ~200ms. If latency were a hard constraint (< 500ms SLA), the trade-off would be: reduce `max_tokens`, drop to `TOP_K_DOCS=2`, and use a smaller model (e.g. `llama-3.1-8b`).

### Data Sensitivity & PII

Ticket bodies and account records may contain customer names, email addresses, error messages with internal system paths, and contract values. This design mitigates leakage by:
- Sending data only to Groq (a contracted API provider with data processing agreements)
- Never logging raw ticket bodies or account data to disk in the application layer
- `.env` excluded from version control via `.gitignore`
- `.env.example` contains only placeholder values — no real credentials

For a production deployment: data masking/redaction before LLM calls, on-premise LLM deployment for highest-sensitivity customers, and field-level encryption for `arr_usd` and contact fields at rest.

### Scaling to 10× Ticket Volume

At 10× volume the first bottleneck is **Groq API rate limits** (free tier: ~30 req/min). The BM25 index is in-memory and adds negligible overhead. Mitigations:
- Queue tickets with a task queue (Celery + Redis) and process in batches
- Cache triage results by ticket hash — identical tickets (duplicates) return instantly
- Upgrade to a paid Groq tier or switch to self-hosted inference for burst capacity
- For Task 2 briefs: cache the AccountBrief per account with a 4-hour TTL; most accounts don't change minute-to-minute

---

## Task 3 — Evaluation Harness

### Test cases

**Task 1 (6 tests including 1 adversarial):**

| ID | Name | Type |
|---|---|---|
| T1-TC1 | P1 — Production pipeline fully down | Normal |
| T1-TC2 | SSO group mapping — known KB issue | Normal |
| T1-TC3 | Billing — invoice seat count discrepancy | Normal |
| T1-TC4 | AnalyticsHub dashboard timeout | Normal |
| T1-TC5 | Feature request — bulk export | Normal |
| T1-TC6-ADV | Vague ticket with no product or error code | **Adversarial** |

**Task 2 (6 tests including 1 adversarial):**

| ID | Name | Type |
|---|---|---|
| T2-TC1 | At-Risk account — Omni Consumer Products ($500k ARR) | Normal |
| T2-TC2 | Healthy account — Wayne Enterprises | Normal |
| T2-TC3 | Churning account — Pinnacle Systems | Normal |
| T2-TC4 | New account — Solaris Data | Normal |
| T2-TC5 | Enterprise At Risk — Vertex Solutions | Normal |
| T2-TC6-ADV | Non-existent account ID | **Adversarial** |

### Scoring

Each test case is scored 0.0–1.0:
- **70% rule-based checks** — field presence, urgency match, quote presence, determinism, metadata integrity
- **30% LLM-as-judge** — contextual quality scored by the same LLM evaluating its own output
- **Pass threshold:** 0.6 quality score
- Exit code 1 if any test fails (CI-friendly)

### Run the harness

```bash
# Full evaluation (both tasks + LLM judge)
python eval_harness.py

# Rules only — faster, no extra LLM calls
python eval_harness.py --no-llm-judge

# Task 1 only
python eval_harness.py --task 1 --no-llm-judge

# Task 2 only
python eval_harness.py --task 2 --no-llm-judge

# Via the Streamlit UI — Tab 3 "Evaluation Harness"
streamlit run app.py
```

Reports are written to `eval_report.json` and `eval_report.md` in the project root.

---

## Running Everything — Quick Reference

```bash
# Navigate to project
cd "d:\Python World\Experiment\Zycus\Task-1"

# ── Verify all imports ────────────────────────────────────
python -c "import triage; import account_brief; import eval_harness; from models import AccountBrief, RiskItem, TriageOutput; print('ALL OK')"

# ── Task 1 CLI ────────────────────────────────────────────
python run_triage.py --ticket-id TKT-10000
python run_triage.py --ticket-id TKT-10003 --stream
python run_triage.py --subject "Pipeline down" --body "ERR_CONNECTION_TIMEOUT on DataBridge Pro."
python run_triage.py --ticket-id TKT-10000 --json

# ── Task 2 CLI ────────────────────────────────────────────
python run_brief.py --account-id ACC-3336
python run_brief.py --account-id ACC-8113
python run_brief.py --account-id ACC-3336 --json

# ── Task 3 Evaluation Harness ─────────────────────────────
python eval_harness.py                         # full eval + LLM judge
python eval_harness.py --no-llm-judge          # rules only (faster)
python eval_harness.py --task 1 --no-llm-judge # Task 1 only
python eval_harness.py --task 2 --no-llm-judge # Task 2 only

# ── Streamlit UI (all three tasks) ───────────────────────
streamlit run app.py

# ── REST API ──────────────────────────────────────────────
uvicorn api:app --reload --port 8000
# then open: http://localhost:8000/docs

# Health check
curl http://localhost:8000/health

# Task 1 triage endpoint
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "Pipeline down", "body": "ERR_CONNECTION_TIMEOUT on DataBridge Pro."}'

# Task 2 — list accounts
curl http://localhost:8000/accounts

# Task 2 — generate brief
curl http://localhost:8000/brief/ACC-3336
```

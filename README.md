# Task 1 — Intelligent Ticket Triage Agent

Ingests a raw support ticket (free-text or JSON) and produces a fully structured triage result — product area, issue category, urgency (P1–P4 with reasoning), relevant knowledge-base article, recommended responder team, and a draft first-response — with zero human labelling.

---

## Architecture

```
Incoming ticket (text or JSON)
        │
        ▼
  ┌─────────────┐   BM25 keyword search   ┌──────────────────────┐
  │  kb_index   │◄───────────────────────►│  KB Markdown files   │
  │ (RAG layer) │   top-3 chunks          │  (9 docs, ~30 chunks)│
  └─────┬───────┘                         └──────────────────────┘
        │ formatted context
        ▼
  ┌─────────────────────────────────────┐
  │  triage.py  (prompt v1.1)           │──► Groq LLM
  │  TRIAGE_PROMPT template + KB chunks │◄── structured JSON
  └─────┬───────────────────────────────┘
        │ validated by Pydantic → TriageOutput
        ▼
  CLI / FastAPI REST / Streamlit UI
```

**RAG strategy:** Each KB markdown file is split on `---` section boundaries (~30 chunks total). Chunks are indexed with BM25 (`rank-bm25`) — no GPU, no external embeddings API required. The top-3 chunks are injected into the prompt. BM25 is well-suited to technical support text where exact error codes and product names matter.

**Prompt versioning:** Every prompt in `prompts.py` has a `version` field and `changelog` list. The current version (`v1.1`) is echoed in every `TriageOutput` for full traceability. A `PROMPT_REGISTRY` dict exposes all prompts for audit and CI validation.

---

## Setup

```bash
cd Task-1

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # Mac/Linux

# 3. Edit .env and set your Groq API key
# GROQ_API_KEY=gsk_...
```

Get a free Groq API key at <https://console.groq.com>. The `llama-3.3-70b-versatile` model is used by default.

---

## Sample Runs

### CLI — triage a dataset ticket

```bash
python run_triage.py --ticket-id TKT-10042
```

Output:
```
────────────────────────────────────────────────────────────
  Ticket ID    : TKT-10042
  Product Area : WorkflowEngine / SSO
  Category     : Integration
  Urgency      : P2  (492 new users blocked; existing users unaffected — major
                      impact but not production-fully-down)
  Responder    : Tier-1 Support
  Reason       : Matches known KB article — SSO group mapping fix.

  KB Match     : ✅  New Users Cannot Authenticate via SSO [high]
  Section      : Symptom: Existing users log in fine; new joiners get an error.

  Draft Response:
    Dear customer, I've identified this as a known SSO group-mapping issue.
    Please navigate to Settings → SSO → Group Mapping and verify the new
    users' IDP group has a role assigned. No reprovisioning is needed after
    the mapping is added. Let me know if you need further assistance.

  Prompt version: v1.1
────────────────────────────────────────────────────────────
```

### CLI — stream tokens in real time

```bash
python run_triage.py --ticket-id TKT-10003 --stream
```

Tokens stream to the terminal as the LLM generates them, then the structured summary is printed.

### CLI — paste free-text ticket

```bash
python run_triage.py \
  --subject "Pipeline stopped after credentials rotated" \
  --body "Our DataBridge Pro pipeline shows ERR_CONNECTION_TIMEOUT since we rotated AWS keys yesterday. 47 engineers are blocked."
```

### CLI — raw JSON output

```bash
python run_triage.py --ticket-id TKT-10042 --json
```

```json
{
  "product_area": "WorkflowEngine / SSO",
  "issue_category": "Integration",
  "urgency": "P2",
  "urgency_reasoning": "...",
  "kb_match": {
    "found": true,
    "doc_title": "New Users Cannot Authenticate via SSO",
    "relevant_section": "Symptom: Existing users log in fine; new joiners get an error.",
    "confidence": "high"
  },
  "responder_team": "Tier-1 Support",
  "responder_reasoning": "...",
  "draft_response": "...",
  "ticket_id": "TKT-10042",
  "prompt_version": "v1.1",
  "retrieved_docs": [...]
}
```

### REST API

```bash
# Start the server
uvicorn api:app --reload --port 8000

# Triage a ticket (synchronous)
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "Pipeline down", "body": "ERR_CONNECTION_TIMEOUT after 30s on DataBridge Pro."}'

# Triage with streaming (Server-Sent Events)
curl -N -X POST http://localhost:8000/triage/stream \
  -H "Content-Type: application/json" \
  -d '{"subject": "Pipeline down", "body": "ERR_CONNECTION_TIMEOUT after 30s."}'

# Health check
curl http://localhost:8000/health
# → {"status": "ok", "service": "ticket-triage-agent"}
```

The streaming endpoint yields `data: <token>` chunks followed by `data: [DONE]` and a final `data: [RESULT] {...}` line containing the full structured JSON.

### Streamlit UI (Bonus +5)

```bash
streamlit run app.py
```

Opens a browser UI with two modes:
- **Paste a ticket** — type or paste any ticket text and click Triage
- **Pick from dataset** — browse all 500 tickets and triage with one click

Displays urgency badge, KB match card, routing recommendation, and the full draft response. Toggle streaming on/off from the sidebar.

---

## File Structure

```
Task-1/
├── config.py                    # All settings loaded from .env
├── prompts.py                   # Versioned prompts — PROMPT_REGISTRY + changelog
├── kb_index.py                  # BM25 RAG index over KB markdown files
├── models.py                    # Pydantic TicketInput / TriageOutput schemas
├── triage.py                    # Core pipeline: sync (triage_ticket) + streaming
├── api.py                       # FastAPI: POST /triage, POST /triage/stream, GET /health
├── run_triage.py                # CLI entry point
├── app.py                       # Streamlit UI (bonus)
├── .github/
│   └── workflows/
│       └── eval.yml             # GitHub Actions CI — runs eval harness on every commit
├── requirements.txt
├── .env.example                 # Required env vars (never commit .env)
└── README.md
```

---

## Bonus Features

| Bonus | Points | Implementation |
|-------|--------|----------------|
| Streamlit UI | +5 | `app.py` — browse dataset or paste free-text; streaming toggle |
| Streaming output | +3 | `triage_ticket_stream()` in `triage.py`; `POST /triage/stream` SSE endpoint; `--stream` CLI flag |
| GitHub Actions CI | +2 | `.github/workflows/eval.yml` — installs deps, smoke-tests imports, runs eval harness on every push/PR |
| Prompt versioning | +2 | `prompts.py` — `version` + `changelog` per prompt; `PROMPT_REGISTRY` for audit; version in every output |

---

## Key Design Decisions

**BM25 over vector embeddings:** Technical support text is keyword-dense (error codes like `ERR_CONNECTION_TIMEOUT`, product names, module names). BM25 retrieves the exact error reference table reliably without needing a GPU or an external embeddings API. For a production system with much larger KB, a hybrid BM25 + dense retrieval approach would be appropriate.

**Groq / llama-3.3-70b:** Free tier, very fast (~1–2s end-to-end), and the 70B model produces well-structured JSON reliably. Temperature is fixed at 0.0 for deterministic output.

**Pydantic validation:** The LLM response is parsed and validated against `TriageOutput` — if the model returns an unexpected urgency value or missing field, it fails loudly with a clear error rather than silently passing bad data downstream.
#   U S - D e l i v e r y -  
 
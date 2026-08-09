# Design Note — Task 4

This document addresses the four required design topics for the production AI system covering Task 1 (Intelligent Ticket Triage) and Task 2 (TAM Account Health Summariser).

---

## 1. Failure Modes

### Failure Mode 1 — LLM returns malformed or incomplete JSON

**What goes wrong:** Despite explicit prompt instructions to return only a JSON object, the LLM occasionally wraps output in markdown fences (` ```json `) or omits required fields when the prompt context is long. Pydantic validation then raises a `ValidationError` and the request fails.

**Detection:** Every pipeline call is wrapped in a try/except. The `_extract_json()` helper logs the raw LLM response before attempting to parse it. If validation fails, the raw response is included in the error message so it can be inspected. In production, a structured logger (e.g. Datadog) would capture failed parse rates as a metric.

**Mitigation:**
- The `_extract_json()` helper already strips markdown fences with regex before parsing.
- A retry with a simplified prompt (shorter KB context, explicit field reminder) would be the first recovery step.
- For critical paths, a fallback rule-based classifier (e.g. keyword matching for urgency) can fill in missing fields rather than hard-failing.

---

### Failure Mode 2 — RAG retrieval returns irrelevant KB chunks (silent quality degradation)

**What goes wrong:** BM25 retrieval can fail on paraphrased or domain-shifted queries. A customer describing `ERR_CONNECTION_TIMEOUT` as "the system freezes" will retrieve low-relevance chunks, causing the LLM to miss the exact troubleshooting step. This is a silent failure — the pipeline returns a result, but the quality is poor. It is harder to detect than a crash.

**Detection:** BM25 scores are logged in `retrieved_docs` in every `TriageOutput`. A monitoring rule that flags responses where all retrieved chunk scores are below a threshold (e.g. < 1.0) would surface low-confidence retrievals before they reach the customer.

**Mitigation:**
- Short-term: increase `TOP_K_DOCS` from 3 to 5 to improve recall at the cost of a slightly larger prompt.
- Medium-term: add semantic (dense) retrieval alongside BM25 — a hybrid re-ranker picks the best of both. This handles paraphrased queries that BM25 misses.
- Long-term: build a feedback loop where agents mark KB matches as helpful/unhelpful. Poor-quality retrievals are used to retrain or tune the retrieval layer.

---

### Failure Mode 3 — Stale account data producing outdated TAM briefs (Task 2)

**What goes wrong:** `accounts.json` is a point-in-time snapshot. If the data is not refreshed and a TAM generates a brief the week before a QBR, the risk signals may reflect a situation that has already been resolved — or miss a new escalation that happened after the last data pull. The brief looks authoritative but is factually outdated.

**Detection:** Every `AccountBrief` includes a `generated_at` UTC timestamp. A UI warning banner can alert the TAM if the underlying account data is older than N days. The `last_qbr_date` and `renewal_date` fields in the account record also provide implicit staleness signals.

**Mitigation:**
- Set a TTL on cached briefs (e.g. 4 hours). Force regeneration before scheduled QBRs.
- In a production deployment, `accounts.json` would be replaced with a live CRM API call (Salesforce/HubSpot) so data is always current at brief generation time.
- Add a data freshness check at the start of `generate_brief()` — if the account record has not been updated in >7 days, surface a warning in the brief itself.

---

## 2. Latency vs Quality Trade-off

The primary trade-off made in this system is **`TOP_K_DOCS=3` (3 retrieved KB chunks) vs higher recall with more chunks**.

Increasing to 5–7 chunks would improve recall on multi-product tickets (e.g. a ticket touching both DataBridge Pro connectors and CloudSync permissions) — the relevant section is more likely to be in the retrieved set. However, each additional chunk adds ~400–600 tokens to the prompt, which increases:
- LLM processing time by ~150–250ms per extra chunk
- Cost per request on paid tiers
- Risk of the LLM being distracted by irrelevant context ("needle in a haystack" degradation)

`TOP_K_DOCS=3` was chosen as the point where retrieval quality is high for single-product tickets (the majority of the dataset) without pushing total prompt length above ~2,000 tokens.

**If latency were the hard constraint (< 500ms SLA):**
- Drop to `TOP_K_DOCS=2`
- Switch from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant` (Groq's fastest model — ~200ms vs ~1s)
- Reduce `max_tokens` from 1024 to 512 (draft responses would be shorter but still functional)
- Cache triage results by a hash of `(subject, body[:200])` — duplicate tickets (common in high-volume support) return instantly without an LLM call

The same principle applies to Task 2: brief generation currently takes 2–4 seconds because the prompt includes full ticket bodies. Switching to truncated summaries (first 200 chars per ticket) would cut latency by ~40% at a modest quality cost.

---

## 3. Data Sensitivity — Handling PII

Ticket bodies and account records in this system contain several categories of potentially sensitive data:

| Data type | Where it appears | Risk |
|---|---|---|
| Customer names | `primary_contact.name`, ticket bodies | PII |
| Company names and ARR | `accounts.json` | Commercially sensitive |
| Error messages with internal paths | Ticket bodies | Infrastructure exposure |
| Contract values and renewal dates | `accounts.json` | Commercially sensitive |
| Support agent names | `tickets.json` | Internal HR data |

**Current mitigations in this design:**

1. **Data stays within the contracted API provider.** All LLM calls go to Groq. No ticket content or account data is sent to any other third-party service. Groq's API terms include data processing provisions standard for enterprise AI APIs.

2. **No data is written to disk by the application.** The triage and brief pipelines operate purely in memory. The only files written are `eval_report.json` and `eval_report.md`, which contain synthetic test data only — no real customer records.

3. **API key isolation.** The `.env` file is excluded from version control via `.gitignore`. The `.env.example` contains only placeholder values. The CI workflow uses GitHub Actions secrets — the key is never in the repository.

4. **No logging of raw inputs.** The application does not log ticket bodies or account data. Only structured outputs (urgency, category, etc.) would be logged in a production observability setup.

**What a production deployment would add:**

- **PII redaction before LLM calls:** a pre-processing step that replaces detected names, emails, and phone numbers with `[REDACTED]` tokens before the prompt is constructed. The original data is only re-inserted into the response at rendering time on the internal UI.
- **On-premise LLM deployment** for customers with strict data residency requirements (e.g. EU GDPR, HIPAA-adjacent healthcare accounts).
- **Field-level encryption** for `arr_usd` and contact fields at rest in any persistent store.
- **Audit log** of which user generated which brief and when — required for SOC 2 compliance.

---

## 4. Scaling — Behaviour at 10× Ticket Volume

The current system processes tickets synchronously, one at a time. At 1× volume this is fine. At 10× volume, the following components become bottlenecks in order:

### What breaks first — Groq API rate limits

The free tier allows approximately 30 requests/minute. At 10× volume with concurrent triage requests, this limit is hit within seconds. Every request beyond the limit returns a `429 Too Many Requests` error.

**Fix:** Move to a paid Groq tier (6,000 req/min on the Developer plan) or implement a task queue (Celery + Redis) that rate-limits outgoing LLM calls to stay within the allowed throughput. The queue also provides retry logic and dead-letter handling for failed LLM calls.

### Second bottleneck — BM25 index rebuild on startup

The BM25 index is built in memory on first retrieval and cached for the process lifetime. At 10× scale with multiple worker processes (e.g. `uvicorn --workers 4`), each worker builds its own independent index on startup, adding 1–2 seconds of cold-start latency per worker and wasting memory.

**Fix:** Build the index once at startup and share it across workers via a shared memory store (e.g. Redis with a serialised index, or a dedicated retrieval microservice).

### Third bottleneck — FastAPI synchronous endpoints

The `/triage` and `/brief/{account_id}` endpoints are currently synchronous — each request blocks a worker thread for the duration of the LLM call (1–4 seconds). At 10× concurrent load, worker threads are exhausted and requests queue up.

**Fix:** Convert the LLM calls to `async` using `AsyncGroq` (Groq's async client). This allows a single worker to handle many in-flight requests concurrently without blocking.

### Summary

| Component | Breaks at | Fix |
|---|---|---|
| Groq rate limit | ~30 req/min | Paid tier + task queue |
| BM25 index per worker | ~4 workers | Shared index via Redis |
| Sync FastAPI workers | ~10 concurrent users | Async LLM calls |
| In-memory data loading | ~1000 accounts/tickets | Background preload + cache TTL |

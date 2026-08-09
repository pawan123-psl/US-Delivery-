"""
app.py
──────
Streamlit UI for:
  Tab 1 — 🎫 Ticket Triage Agent          (Task 1)
  Tab 2 — 📋 TAM Account Health Brief     (Task 2)

Run:
  streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import ACCOUNTS_PATH, TICKETS_PATH
from models import TicketInput
from triage import triage_ticket, triage_ticket_stream


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Triage & TAM Brief Agent",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Shared styling ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Task 1 urgency badges */
    .urgency-p1 { background:#fee2e2; color:#991b1b; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p2 { background:#fef3c7; color:#92400e; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p3 { background:#dbeafe; color:#1e40af; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p4 { background:#dcfce7; color:#166534; padding:4px 12px; border-radius:8px; font-weight:700; }

    .section-title { font-size:1rem; font-weight:600; color:#374151; margin-bottom:4px; }
    .kb-match-found { background:#ecfdf5; color:#065f46; border-left:4px solid #10b981; padding:8px 12px; border-radius:4px; }
    .kb-match-none  { background:#f9fafb; color:#374151; border-left:4px solid #9ca3af; padding:8px 12px; border-radius:4px; }
    .draft-box      { background:#f8fafc; color:#1e293b; border:1px solid #e2e8f0; border-radius:8px; padding:16px; font-family:sans-serif; white-space:pre-wrap; line-height:1.6; }

    /* Task 2 brief sections */
    .brief-summary  { background:#f0f9ff; color:#0c4a6e; border-left:4px solid #0ea5e9; padding:14px 16px; border-radius:6px; line-height:1.7; }
    .risk-card      { background:#fff7ed; color:#78350f; border-left:4px solid #f97316; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
    .risk-quote     { font-style:italic; color:#92400e; margin-top:4px; }
    .tp-card        { background:#f0fdf4; color:#14532d; border-left:4px solid #22c55e; padding:8px 14px; border-radius:6px; margin-bottom:6px; }
    .health-at-risk { background:#fef2f2; color:#b91c1c; padding:4px 10px; border-radius:6px; font-weight:600; }
    .health-healthy { background:#dcfce7; color:#15803d; padding:4px 10px; border-radius:6px; font-weight:600; }
    .health-other   { background:#f1f5f9; color:#475569; padding:4px 10px; border-radius:6px; font-weight:600; }
</style>
""", unsafe_allow_html=True)


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_tickets():
    """Load all tickets from the dataset (Task 1 and Task 2)."""
    return json.loads(TICKETS_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_accounts():
    """Task 2 — Load all accounts for the dropdown."""
    return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 AI Support Tools")
    st.caption("Task 1: Ticket Triage  |  Task 2: TAM Brief")
    st.divider()

    # Task 1 sidebar controls
    st.markdown("**Task 1 — Triage Settings**")
    mode = st.radio("Input mode", ["Paste a ticket", "Pick from dataset"])
    use_stream = st.toggle("⚡ Streaming output", value=True)
    st.divider()

    st.markdown("**Urgency legend**")
    st.markdown(
        '<span class="urgency-p1">P1 Critical</span>&nbsp;&nbsp;'
        '<span class="urgency-p2">P2 Major</span><br><br>'
        '<span class="urgency-p3">P3 Moderate</span>&nbsp;&nbsp;'
        '<span class="urgency-p4">P4 Low</span>',
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🎫 Ticket Triage", "📋 TAM Account Brief"])


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — Ticket Triage (Task 1, unchanged logic)                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.title("🎫 Intelligent Ticket Triage")
    st.caption("Classifies product area, urgency, and surfaces the right KB article — instantly.")

    ticket_to_triage: TicketInput | None = None

    if mode == "Paste a ticket":
        col1, col2 = st.columns([1, 2])
        with col1:
            subject = st.text_input("Subject", placeholder="e.g. Pipeline stopped processing")
            plan_tier = st.selectbox(
                "Plan tier (optional)",
                ["", "Starter", "Professional", "Business", "Enterprise"],
            )
        with col2:
            body = st.text_area(
                "Ticket body", height=200,
                placeholder="Paste the full ticket text here...",
            )

        if st.button("🚀 Triage this ticket", type="primary", disabled=not body.strip()):
            ticket_to_triage = TicketInput(
                subject=subject or "(no subject)",
                body=body,
                plan_tier=plan_tier or None,
            )

    elif mode == "Pick from dataset":
        tickets = load_tickets()
        options = {f"{t['ticket_id']} — {t['subject'][:60]}": t for t in tickets}
        choice = st.selectbox("Select a ticket", list(options.keys()))
        selected = options[choice]

        with st.expander("📄 Ticket preview", expanded=True):
            st.markdown(f"**Subject:** {selected['subject']}")
            st.markdown(
                f"**Product:** {selected.get('product', '—')}  |  "
                f"**Status:** {selected.get('status', '—')}  |  "
                f"**Plan:** {selected.get('plan_tier', '—')}"
            )
            st.text(selected["body"])

        if st.button("🚀 Triage this ticket", type="primary"):
            ticket_to_triage = TicketInput(
                ticket_id=selected["ticket_id"],
                subject=selected["subject"],
                body=selected["body"],
                account_id=selected.get("account_id"),
                plan_tier=selected.get("plan_tier"),
            )

    # ── Run triage ────────────────────────────────────────────────────────────
    if ticket_to_triage is not None:
        st.divider()
        st.subheader("📊 Triage Result")

        result = None

        if use_stream:
            stream_placeholder = st.empty()
            full_text = ""
            result_json = None

            with st.spinner("Analysing ticket..."):
                for chunk in triage_ticket_stream(ticket_to_triage):
                    if chunk.startswith("data: [RESULT]"):
                        result_json = chunk.replace("data: [RESULT] ", "").strip()
                    elif chunk == "data: [DONE]\n":
                        stream_placeholder.empty()
                    else:
                        full_text += chunk.replace("data: ", "")
                        stream_placeholder.code(full_text, language="json")

            if result_json:
                from models import TriageOutput
                result = TriageOutput.model_validate(json.loads(result_json))
        else:
            with st.spinner("Analysing ticket..."):
                result = triage_ticket(ticket_to_triage)

        if result:
            m1, m2, m3, m4 = st.columns(4)
            urgency_css = {
                "P1": "urgency-p1", "P2": "urgency-p2",
                "P3": "urgency-p3", "P4": "urgency-p4",
            }.get(result.urgency, "urgency-p4")

            m1.metric("Urgency", result.urgency)
            m2.metric("Category", result.issue_category)
            m3.metric("Responder", result.responder_team)
            m4.metric("KB Match", "✅ Found" if result.kb_match.found else "❌ None")

            st.divider()

            left, right = st.columns(2)

            with left:
                st.markdown('<p class="section-title">🏷 Classification</p>', unsafe_allow_html=True)
                st.markdown(f"**Product area:** {result.product_area}")
                st.markdown(f"**Issue category:** {result.issue_category}")
                st.markdown(
                    f'**Urgency:** <span class="{urgency_css}">{result.urgency}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(result.urgency_reasoning)

                st.markdown(
                    '<p class="section-title" style="margin-top:16px">📡 Routing</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Team:** {result.responder_team}")
                st.caption(result.responder_reasoning)

            with right:
                st.markdown('<p class="section-title">📚 Knowledge Base</p>', unsafe_allow_html=True)
                if result.kb_match.found:
                    st.markdown(
                        f'<div class="kb-match-found">'
                        f'<strong>{result.kb_match.doc_title}</strong><br>'
                        f'Section: <em>{result.kb_match.relevant_section or "—"}</em><br>'
                        f'Confidence: <strong>{result.kb_match.confidence}</strong>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="kb-match-none">No matching KB article found.</div>',
                        unsafe_allow_html=True,
                    )

                with st.expander("Retrieved KB chunks", expanded=False):
                    for doc in (result.retrieved_docs or []):
                        st.markdown(
                            f"- **{doc['source']}** › {doc['heading']}  "
                            f"_(score: {doc['score']:.3f})_"
                        )

            st.divider()

            st.markdown('<p class="section-title">✉️ Draft First Response</p>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="draft-box">{result.draft_response}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Prompt version: {result.prompt_version}")

            st.divider()

            with st.expander("🔍 Raw JSON output"):
                st.json(result.model_dump())


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — TAM Account Health Brief  (Task 2)                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

with tab2:
    # Task 2 — TAM Account Health Brief UI
    st.title("📋 TAM Account Health Brief")
    st.caption(
        "Select an account to generate a 3-section brief: "
        "Executive Summary · Risks & Flags · Talking Points"
    )

    # Task 2 — Load accounts for dropdown
    try:
        accounts_data = load_accounts()
        account_options = {
            f"{a['account_id']} — {a.get('company', '')}": a["account_id"]
            for a in accounts_data
        }
        use_dropdown = True
    except Exception:
        use_dropdown = False
        account_options = {}

    # Task 2 — Account selection: dropdown (preferred) or manual text input
    col_left, col_right = st.columns([2, 1])
    with col_left:
        if use_dropdown and account_options:
            selected_label = st.selectbox(
                "Select an account",
                options=list(account_options.keys()),
                help="Choose from loaded accounts.json",
            )
            account_id_input = account_options[selected_label]
        else:
            account_id_input = st.text_input(
                "Account ID",
                placeholder="e.g. ACC-3336",
                help="Enter the account ID manually",
            )

    with col_right:
        st.markdown("<br>", unsafe_allow_html=True)   # vertical align the button
        run_brief = st.button(
            "📋 Generate Brief",
            type="primary",
            disabled=not (account_id_input or "").strip(),
        )

    # Task 2 — Show account preview metadata if available
    if use_dropdown and account_options and account_id_input:
        matched = [a for a in accounts_data if a["account_id"] == account_id_input]
        if matched:
            acct = matched[0]
            health = acct.get("health_status", "Unknown")
            health_css = (
                "health-at-risk" if "risk" in health.lower()
                else "health-healthy" if health.lower() == "healthy"
                else "health-other"
            )
            with st.expander("Account snapshot", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Plan", acct.get("plan_tier", "—"))
                c2.metric("ARR", f"${acct.get('arr_usd', 0):,.0f}" if acct.get("arr_usd") else "—")
                c3.metric("Open Tickets", acct.get("open_tickets", "—"))
                c4.metric("P1s (30d)", acct.get("p1_tickets_last_30d", "—"))
                st.markdown(
                    f"**Health:** <span class=\"{health_css}\">{health}</span>  "
                    f"&nbsp;|&nbsp; **TAM:** {acct.get('tam', '—')}  "
                    f"&nbsp;|&nbsp; **Renewal:** {acct.get('renewal_date', '—')}",
                    unsafe_allow_html=True,
                )
                notes = acct.get("escalation_notes", [])
                if notes:
                    st.warning("⚠️ Escalation notes: " + "  •  ".join(notes))

    # Task 2 — Generate and display the brief
    if run_brief and account_id_input.strip():
        from account_brief import generate_brief

        with st.spinner(f"Generating brief for {account_id_input} …"):
            try:
                brief = generate_brief(account_id_input.strip())
                brief_error = None
            except ValueError as exc:
                brief = None
                brief_error = str(exc)
            except EnvironmentError as exc:
                brief = None
                brief_error = f"Configuration error: {exc}"
            except Exception as exc:
                brief = None
                brief_error = f"Unexpected error: {exc}"

        if brief_error:
            st.error(f"❌ {brief_error}")

        elif brief:
            st.divider()

            # Task 2 — Brief header metrics
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("Company", brief.company)
            h2.metric("TAM", brief.tam)
            h3.metric("Tickets Analysed", brief.tickets_analysed)
            h4.metric("Health", brief.health_status)

            st.divider()

            # ── Section 1: Executive Summary ─────────────────────────────────
            st.markdown("### 📋 Executive Summary")
            st.markdown(
                f'<div class="brief-summary">{brief.executive_summary}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Section 2: Risks & Flagged Issues ────────────────────────────
            st.markdown("### ⚠️ Open Risks & Flagged Issues")
            if not brief.risks:
                st.success("✅ No churn risks or escalation signals identified in the last 90 days.")
            else:
                for risk in brief.risks:
                    ticket_ref = f" `{risk.ticket_id}`" if risk.ticket_id else ""
                    st.markdown(
                        f'<div class="risk-card">'
                        f'<strong>{ticket_ref} {risk.description}</strong>'
                        f'<div class="risk-quote">"{risk.ticket_quote}"</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Section 3: Talking Points ─────────────────────────────────────
            st.markdown("### 💬 Recommended Talking Points")
            if not brief.talking_points:
                st.info("No talking points generated.")
            else:
                for point in brief.talking_points:
                    st.markdown(
                        f'<div class="tp-card">✔ {point}</div>',
                        unsafe_allow_html=True,
                    )

            st.divider()
            st.caption(f"Generated at {brief.generated_at}  |  temperature=0.0 (deterministic)")

            # Task 2 — Raw JSON expander
            with st.expander("🔍 Raw JSON output"):
                st.json(brief.model_dump())

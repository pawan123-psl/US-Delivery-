"""
app.py
──────
Streamlit UI for the Ticket Triage Agent (Bonus: +5 marks).

A clean, non-technical UI that a support agent or TAM can use to:
  - Paste a ticket and instantly see the triage result
  - Browse the dataset and triage any ticket with one click
  - See streaming output token-by-token

Run:
  streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import TICKETS_PATH
from models import TicketInput
from triage import triage_ticket, triage_ticket_stream


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎫 Ticket Triage Agent",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .urgency-p1 { background:#fee2e2; color:#991b1b; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p2 { background:#fef3c7; color:#92400e; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p3 { background:#dbeafe; color:#1e40af; padding:4px 12px; border-radius:8px; font-weight:700; }
    .urgency-p4 { background:#dcfce7; color:#166534; padding:4px 12px; border-radius:8px; font-weight:700; }
    .section-title { font-size:1rem; font-weight:600; color:#374151; margin-bottom:4px; }
    .kb-match-found { background:#ecfdf5; color:#065f46; border-left:4px solid #10b981; padding:8px 12px; border-radius:4px; }
    .kb-match-none { background:#f9fafb; color:#374151; border-left:4px solid #9ca3af; padding:8px 12px; border-radius:4px; }
    .draft-box { background:#f8fafc; color:#1e293b; border:1px solid #e2e8f0; border-radius:8px; padding:16px; font-family:sans-serif; white-space:pre-wrap; line-height:1.6; }
</style>
""", unsafe_allow_html=True)


# ── Load dataset ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_tickets():
    return json.loads(TICKETS_PATH.read_text(encoding="utf-8"))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎫 Triage Agent")
    st.caption("AI-powered support ticket triage")
    st.divider()
    mode = st.radio("Input mode", ["Paste a ticket", "Pick from dataset"])
    st.divider()
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


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("🎫 Intelligent Ticket Triage")
st.caption("Classifies product area, urgency, and surfaces the right KB article — instantly.")

ticket_to_triage: TicketInput | None = None

if mode == "Paste a ticket":
    col1, col2 = st.columns([1, 2])
    with col1:
        subject = st.text_input("Subject", placeholder="e.g. Pipeline stopped processing")
        plan_tier = st.selectbox("Plan tier (optional)", ["", "Starter", "Professional", "Business", "Enterprise"])
    with col2:
        body = st.text_area("Ticket body", height=200,
                            placeholder="Paste the full ticket text here...")

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
        st.markdown(f"**Product:** {selected.get('product', '—')}  |  "
                    f"**Status:** {selected.get('status', '—')}  |  "
                    f"**Plan:** {selected.get('plan_tier', '—')}")
        st.text(selected["body"])

    if st.button("🚀 Triage this ticket", type="primary"):
        ticket_to_triage = TicketInput(
            ticket_id=selected["ticket_id"],
            subject=selected["subject"],
            body=selected["body"],
            account_id=selected.get("account_id"),
            plan_tier=selected.get("plan_tier"),
        )


# ── Run triage ────────────────────────────────────────────────────────────────
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
        # ── Row 1: key metrics ────────────────────────────────────────────
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

        # ── Row 2: details ────────────────────────────────────────────────
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

            st.markdown('<p class="section-title" style="margin-top:16px">📡 Routing</p>',
                        unsafe_allow_html=True)
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
                    st.markdown(f"- **{doc['source']}** › {doc['heading']}  "
                                f"_(score: {doc['score']:.3f})_")

        st.divider()

        # ── Draft response ────────────────────────────────────────────────
        st.markdown('<p class="section-title">✉️ Draft First Response</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="draft-box">{result.draft_response}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Prompt version: {result.prompt_version}")

        st.divider()

        # ── Raw JSON ──────────────────────────────────────────────────────
        with st.expander("🔍 Raw JSON output"):
            st.json(result.model_dump())

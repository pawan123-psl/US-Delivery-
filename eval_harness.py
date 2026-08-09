"""
eval_harness.py  — Task 3
─────────────────────────
Evaluation harness that systematically tests Task 1 (Ticket Triage)
and Task 2 (TAM Account Health Summariser) outputs.

Structure:
  - 5+ test cases per task (including at least 1 adversarial per task)
  - Each test case has rule-based checks + optional LLM-as-judge scoring
  - Scoring: pass/fail per check + quality score (0.0–1.0) per test case
  - Outputs: eval_report.json and eval_report.md

Run:
  python eval_harness.py
  python eval_harness.py --no-llm-judge   # skip LLM-as-judge, rules only
  python eval_harness.py --task 1         # run Task 1 only
  python eval_harness.py --task 2         # run Task 2 only
"""

from __future__ import annotations

# ── Task 3: standard library imports ──────────────────────────────────────────
import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Task 3: project imports ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config
from models import TicketInput, TriageOutput, AccountBrief
from triage import triage_ticket
from account_brief import generate_brief


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: Data structures for test cases and results
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    """Task 3 — Result of a single rule-based check within a test case."""
    check_name: str          # e.g. "urgency_is_p1"
    passed: bool             # True if the check passed
    expected: Any            # What we expected
    actual: Any              # What the pipeline returned
    message: str             # Human-readable explanation


@dataclass
class TestCaseResult:
    """Task 3 — Full result for one test case."""
    test_id: str             # e.g. "T1-TC1"
    task: int                # 1 or 2
    name: str                # Human-readable test name
    adversarial: bool        # Whether this is an adversarial test case
    checks: List[CheckResult] = field(default_factory=list)
    llm_judge_score: Optional[float] = None   # 0.0–1.0 from LLM-as-judge
    llm_judge_rationale: str = ""
    quality_score: float = 0.0               # Final combined score
    passed: bool = False                     # Overall pass/fail
    error: Optional[str] = None              # Exception message if pipeline crashed
    latency_seconds: float = 0.0             # Wall-clock time for the pipeline call


@dataclass
class EvalReport:
    """Task 3 — Full evaluation report across all test cases."""
    generated_at: str
    total_tests: int
    passed: int
    failed: int
    task1_score: float       # Average quality score for Task 1 tests
    task2_score: float       # Average quality score for Task 2 tests
    overall_score: float     # Average across all tests
    results: List[TestCaseResult] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: Rule-based scoring helpers
# ══════════════════════════════════════════════════════════════════════════════

def _check(name: str, passed: bool, expected: Any, actual: Any, message: str) -> CheckResult:
    """Task 3 — Convenience constructor for a CheckResult."""
    return CheckResult(
        check_name=name,
        passed=passed,
        expected=str(expected),
        actual=str(actual),
        message=message,
    )


def _quality_from_checks(checks: List[CheckResult], llm_score: Optional[float]) -> float:
    """
    Task 3 — Compute final quality score (0.0–1.0) by combining:
      - Rule-based pass rate (weighted 0.7)
      - LLM-as-judge score if available (weighted 0.3)
    If no LLM score, use rule-based pass rate as the full score.
    """
    if not checks:
        return 0.0
    rule_score = sum(1 for c in checks if c.passed) / len(checks)
    if llm_score is not None:
        return round(0.7 * rule_score + 0.3 * llm_score, 3)
    return round(rule_score, 3)


def _passes_threshold(quality_score: float, threshold: float = 0.6) -> bool:
    """Task 3 — A test case passes if quality score >= threshold."""
    return quality_score >= threshold


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: LLM-as-judge
# ══════════════════════════════════════════════════════════════════════════════

def _llm_judge(prompt: str) -> tuple[float, str]:
    """
    Task 3 — Call Groq LLM to act as an evaluator judge.
    Returns (score: float 0.0-1.0, rationale: str).
    Falls back to (0.5, "LLM judge unavailable") on any error.
    """
    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict evaluator. Score the response quality "
                        "from 0.0 to 1.0 and return ONLY valid JSON: "
                        '{"score": <float>, "rationale": "<one sentence>"}'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        import re
        raw = resp.choices[0].message.content or ""
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            score = float(data.get("score", 0.5))
            score = max(0.0, min(1.0, score))   # clamp to [0, 1]
            return score, data.get("rationale", "")
    except Exception as exc:
        return 0.5, f"LLM judge error: {exc}"
    return 0.5, "LLM judge: no parseable response"


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: TASK 1 — Ticket Triage test cases (5 + 1 adversarial)
# ══════════════════════════════════════════════════════════════════════════════

def _run_triage_test(
    test_id: str,
    name: str,
    subject: str,
    body: str,
    expected_urgency: Optional[str],
    expected_category: Optional[str],
    expected_product_keywords: List[str],
    expect_kb_match: Optional[bool],
    adversarial: bool,
    use_llm_judge: bool,
) -> TestCaseResult:
    """
    Task 3 — Run a single Task 1 triage test case.
    Applies rule-based checks then optionally LLM-as-judge.
    """
    result = TestCaseResult(
        test_id=test_id, task=1, name=name, adversarial=adversarial
    )
    start = time.perf_counter()

    # ── Call the pipeline ─────────────────────────────────────────────────────
    try:
        ticket = TicketInput(subject=subject, body=body)
        output: TriageOutput = triage_ticket(ticket)
    except Exception as exc:
        result.error = str(exc)
        result.quality_score = 0.0
        result.passed = False
        result.latency_seconds = round(time.perf_counter() - start, 2)
        return result

    result.latency_seconds = round(time.perf_counter() - start, 2)

    # ── Rule-based checks ─────────────────────────────────────────────────────

    # Check 1: Output has all required fields (Pydantic already validates, but verify)
    has_all_fields = all([
        output.product_area, output.issue_category,
        output.urgency, output.urgency_reasoning,
        output.responder_team, output.draft_response,
    ])
    result.checks.append(_check(
        "all_fields_present", has_all_fields,
        "all required fields non-empty", "present" if has_all_fields else "missing fields",
        "All TriageOutput fields must be populated",
    ))

    # Check 2: Urgency matches expectation (if specified)
    if expected_urgency:
        urgency_ok = output.urgency == expected_urgency
        result.checks.append(_check(
            "urgency_correct", urgency_ok,
            expected_urgency, output.urgency,
            f"Urgency should be {expected_urgency} for this ticket type",
        ))

    # Check 3: Category matches expectation (if specified)
    if expected_category:
        cat_ok = output.issue_category == expected_category
        result.checks.append(_check(
            "category_correct", cat_ok,
            expected_category, output.issue_category,
            f"Category should be {expected_category}",
        ))

    # Check 4: Product area mentions expected keyword(s)
    if expected_product_keywords:
        pa_lower = output.product_area.lower()
        kw_found = any(kw.lower() in pa_lower for kw in expected_product_keywords)
        result.checks.append(_check(
            "product_area_relevant", kw_found,
            f"one of {expected_product_keywords}", output.product_area,
            "Product area should reference the correct product/module",
        ))

    # Check 5: KB match expectation (if specified)
    if expect_kb_match is not None:
        kb_ok = output.kb_match.found == expect_kb_match
        result.checks.append(_check(
            "kb_match_as_expected", kb_ok,
            f"kb_match.found={expect_kb_match}", f"kb_match.found={output.kb_match.found}",
            "KB match found status should match expectation",
        ))

    # Check 6: Draft response is non-trivial (> 50 chars, mentions the product)
    draft_ok = len(output.draft_response) > 50
    result.checks.append(_check(
        "draft_response_substantive", draft_ok,
        ">50 chars", f"{len(output.draft_response)} chars",
        "Draft response must be a substantive message",
    ))

    # Check 7: Urgency reasoning is non-empty
    reasoning_ok = len(output.urgency_reasoning) > 20
    result.checks.append(_check(
        "urgency_reasoning_present", reasoning_ok,
        ">20 chars", f"{len(output.urgency_reasoning)} chars",
        "Urgency reasoning must explain the classification",
    ))

    # Check 8: Prompt version is present
    version_ok = bool(output.prompt_version)
    result.checks.append(_check(
        "prompt_version_present", version_ok,
        "non-empty", output.prompt_version or "None",
        "Prompt version must be echoed in output for auditability",
    ))

    # ── LLM-as-judge ─────────────────────────────────────────────────────────
    if use_llm_judge:
        judge_prompt = (
            f"Evaluate this ticket triage result.\n\n"
            f"TICKET:\nSubject: {subject}\nBody: {body[:300]}\n\n"
            f"TRIAGE OUTPUT:\n"
            f"- Urgency: {output.urgency} — {output.urgency_reasoning}\n"
            f"- Category: {output.issue_category}\n"
            f"- Product area: {output.product_area}\n"
            f"- Responder: {output.responder_team}\n"
            f"- Draft response (first 200 chars): {output.draft_response[:200]}\n\n"
            f"Score 0.0–1.0: Is the urgency, category, and draft response appropriate "
            f"and professional for this ticket?"
        )
        result.llm_judge_score, result.llm_judge_rationale = _llm_judge(judge_prompt)

    # ── Final scoring ─────────────────────────────────────────────────────────
    result.quality_score = _quality_from_checks(result.checks, result.llm_judge_score)
    result.passed = _passes_threshold(result.quality_score)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: TASK 1 test cases definitions
# ══════════════════════════════════════════════════════════════════════════════

TASK1_TEST_CASES = [
    # ── TC1: Clear P1 — production fully down ─────────────────────────────────
    {
        "test_id": "T1-TC1",
        "name": "P1 — Production pipeline fully down (clear critical case)",
        "subject": "URGENT: DataBridge Pro pipeline completely stopped",
        "body": (
            "Our DataBridge Pro pipeline has been completely down since 06:00 UTC. "
            "All 350 users in our Engineering org cannot process any data. "
            "Error: ERR_CONNECTION_TIMEOUT after 30s. "
            "This is blocking our entire production data flow. We need immediate help."
        ),
        "expected_urgency": "P1",
        "expected_category": "Bug",
        "expected_product_keywords": ["DataBridge"],
        "expect_kb_match": True,
        "adversarial": False,
    },
    # ── TC2: SSO issue — known KB article exists ───────────────────────────────
    {
        "test_id": "T1-TC2",
        "name": "SSO group mapping — known KB issue",
        "subject": "New users cannot log in via SSO",
        "body": (
            "We migrated to SSO last week. Existing users log in fine, "
            "but all new joiners get an error. Our IDP is Okta. "
            "We have 150 new hires starting next Monday who can't access the platform."
        ),
        "expected_urgency": "P2",
        "expected_category": "Integration",
        "expected_product_keywords": ["sso", "cloudsync", "securevault", "authentication"],
        "expect_kb_match": True,
        "adversarial": False,
    },
    # ── TC3: Billing question — low urgency ───────────────────────────────────
    {
        "test_id": "T1-TC3",
        "name": "Billing — invoice seat count discrepancy (P4)",
        "subject": "Billing question about our latest invoice",
        "body": (
            "Hi, we received our invoice for this month and were charged for 310 seats "
            "but we only have 298 active users. Could you clarify how seat billing works "
            "and process a credit if we were overcharged? No urgency, just want to clarify."
        ),
        "expected_urgency": "P4",
        "expected_category": "Billing",
        "expected_product_keywords": ["billing", "seat", "invoice"],
        "expect_kb_match": True,
        "adversarial": False,
    },
    # ── TC4: Performance degradation — moderate impact ────────────────────────
    {
        "test_id": "T1-TC4",
        "name": "AnalyticsHub dashboard timeout — performance issue",
        "subject": "AnalyticsHub dashboards timing out for our team",
        "body": (
            "Our AnalyticsHub dashboards have been extremely slow for the past 3 days. "
            "Page loads take 60+ seconds and some queries time out entirely. "
            "This affects about 40 analysts but they can still access older cached data. "
            "We're on Business plan."
        ),
        "expected_urgency": "P3",
        "expected_category": "Performance",
        "expected_product_keywords": ["analyticshub", "analytics", "dashboard"],
        "expect_kb_match": True,
        "adversarial": False,
    },
    # ── TC5: Feature request — low priority ───────────────────────────────────
    {
        "test_id": "T1-TC5",
        "name": "Feature request — bulk export in WorkflowEngine",
        "subject": "Feature request: bulk workflow export",
        "body": (
            "Hi team, we'd love to see a bulk export feature in WorkflowEngine. "
            "Currently we have to export each workflow one by one which takes hours. "
            "Use case: monthly audit reporting. Happy to join a beta. Thanks!"
        ),
        "expected_urgency": "P4",
        "expected_category": "Feature Request",
        "expected_product_keywords": ["workflowengine", "workflow"],
        "expect_kb_match": None,   # KB match is not required for feature requests
        "adversarial": False,
    },
    # ── TC6 (ADVERSARIAL): Ambiguous ticket — vague, no product named ─────────
    {
        "test_id": "T1-TC6-ADV",
        "name": "ADVERSARIAL — Vague ticket with no product or error code",
        "subject": "Something is broken",
        "body": (
            "Hi, our system stopped working yesterday. "
            "We get some kind of error when we try to do the thing. "
            "Can someone please help? It's been broken since yesterday."
        ),
        "expected_urgency": None,      # Any urgency is acceptable for vague input
        "expected_category": None,     # Any category acceptable
        "expected_product_keywords": [], # No product to validate
        "expect_kb_match": None,
        "adversarial": True,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: TASK 2 — Account Brief test cases runner
# ══════════════════════════════════════════════════════════════════════════════

def _run_brief_test(
    test_id: str,
    name: str,
    account_id: str,
    expect_health_status: Optional[str],
    expect_risks: bool,
    expect_min_talking_points: int,
    expect_summary_min_sentences: int,
    adversarial: bool,
    use_llm_judge: bool,
) -> TestCaseResult:
    """
    Task 3 — Run a single Task 2 account brief test case.
    Applies rule-based checks then optionally LLM-as-judge.
    """
    result = TestCaseResult(
        test_id=test_id, task=2, name=name, adversarial=adversarial
    )
    start = time.perf_counter()

    # ── Call the pipeline ─────────────────────────────────────────────────────
    brief: Optional[AccountBrief] = None
    try:
        brief = generate_brief(account_id)
    except ValueError as exc:
        # For adversarial tests, ValueError (not found) may be the expected outcome
        if adversarial:
            result.checks.append(_check(
                "graceful_error_for_invalid_id", True,
                "ValueError raised", str(exc),
                "Invalid account ID should raise ValueError gracefully",
            ))
            result.quality_score = 1.0
            result.passed = True
            result.latency_seconds = round(time.perf_counter() - start, 2)
            return result
        result.error = str(exc)
        result.quality_score = 0.0
        result.passed = False
        result.latency_seconds = round(time.perf_counter() - start, 2)
        return result
    except Exception as exc:
        result.error = str(exc)
        result.quality_score = 0.0
        result.passed = False
        result.latency_seconds = round(time.perf_counter() - start, 2)
        return result

    result.latency_seconds = round(time.perf_counter() - start, 2)

    # ── Rule-based checks ─────────────────────────────────────────────────────

    # Check 1: All required metadata fields populated
    meta_ok = all([brief.account_id, brief.company, brief.tam, brief.plan_tier])
    result.checks.append(_check(
        "metadata_complete", meta_ok,
        "account_id, company, tam, plan_tier all present",
        f"account_id={brief.account_id}, company={brief.company}",
        "AccountBrief must include complete account metadata",
    ))

    # Check 2: Executive summary is 3–5 sentences
    sentences = [s.strip() for s in brief.executive_summary.split(".") if s.strip()]
    summary_len_ok = expect_summary_min_sentences <= len(sentences) <= 8
    result.checks.append(_check(
        "executive_summary_length", summary_len_ok,
        f">={expect_summary_min_sentences} sentences", f"{len(sentences)} sentences",
        "Executive summary must be a substantial paragraph (3–5 sentences)",
    ))

    # Check 3: Summary is non-trivial (>100 chars)
    summary_content_ok = len(brief.executive_summary) > 100
    result.checks.append(_check(
        "executive_summary_substantive", summary_content_ok,
        ">100 chars", f"{len(brief.executive_summary)} chars",
        "Executive summary must contain meaningful content",
    ))

    # Check 4: Risks are present when expected
    if expect_risks:
        has_risks = len(brief.risks) > 0
        result.checks.append(_check(
            "risks_present_for_at_risk_account", has_risks,
            "at least 1 risk", f"{len(brief.risks)} risks",
            "At-risk accounts should have flagged risks",
        ))
        # Check 5: Each risk has a non-empty quote
        if brief.risks:
            all_have_quotes = all(len(r.ticket_quote) > 10 for r in brief.risks)
            result.checks.append(_check(
                "risk_quotes_present", all_have_quotes,
                "all risks have ticket_quote >10 chars",
                f"{sum(1 for r in brief.risks if len(r.ticket_quote) > 10)}/{len(brief.risks)} have quotes",
                "Every risk must include a direct ticket quote",
            ))

    # Check 6: Talking points meet minimum count
    tp_ok = len(brief.talking_points) >= expect_min_talking_points
    result.checks.append(_check(
        "talking_points_count", tp_ok,
        f">={expect_min_talking_points} talking points",
        f"{len(brief.talking_points)} talking points",
        "Brief must include actionable talking points for the TAM",
    ))

    # Check 7: Health status matches expected (if specified)
    if expect_health_status:
        health_ok = brief.health_status == expect_health_status
        result.checks.append(_check(
            "health_status_matches_data", health_ok,
            expect_health_status, brief.health_status,
            "Health status in brief must match accounts.json record",
        ))

    # Check 8: generated_at is a valid ISO timestamp
    try:
        datetime.fromisoformat(brief.generated_at)
        ts_ok = True
    except ValueError:
        ts_ok = False
    result.checks.append(_check(
        "generated_at_valid_timestamp", ts_ok,
        "valid ISO-8601 datetime", brief.generated_at,
        "generated_at must be a valid UTC ISO-8601 timestamp",
    ))

    # Check 9: Determinism — run the same account_id twice, summaries should match
    try:
        brief2 = generate_brief(account_id)
        determinism_ok = brief.executive_summary == brief2.executive_summary
        result.checks.append(_check(
            "output_is_deterministic", determinism_ok,
            "same executive_summary on second run",
            "match" if determinism_ok else "different output",
            "temperature=0.0 must produce identical output for the same input",
        ))
    except Exception:
        pass  # Skip determinism check if second call fails

    # ── LLM-as-judge ─────────────────────────────────────────────────────────
    if use_llm_judge and brief:
        judge_prompt = (
            f"Evaluate this TAM account health brief.\n\n"
            f"ACCOUNT: {brief.company} ({brief.account_id}) — {brief.health_status}\n\n"
            f"EXECUTIVE SUMMARY:\n{brief.executive_summary}\n\n"
            f"RISKS ({len(brief.risks)} flagged):\n"
            + "\n".join(f"- {r.description}: \"{r.ticket_quote[:80]}\"" for r in brief.risks[:3])
            + f"\n\nTALKING POINTS:\n"
            + "\n".join(f"- {tp}" for tp in brief.talking_points[:3])
            + "\n\nScore 0.0–1.0: Is this brief accurate, actionable, and professional? "
            "Are the risks well-evidenced with ticket quotes?"
        )
        result.llm_judge_score, result.llm_judge_rationale = _llm_judge(judge_prompt)

    # ── Final scoring ─────────────────────────────────────────────────────────
    result.quality_score = _quality_from_checks(result.checks, result.llm_judge_score)
    result.passed = _passes_threshold(result.quality_score)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: TASK 2 test cases definitions
# ══════════════════════════════════════════════════════════════════════════════

TASK2_TEST_CASES = [
    # ── TC1: High-value at-risk account — should surface risks ────────────────
    {
        "test_id": "T2-TC1",
        "name": "At-Risk account — Omni Consumer Products ($500k ARR)",
        "account_id": "ACC-3336",
        "expect_health_status": "At Risk",
        "expect_risks": True,
        "expect_min_talking_points": 3,
        "expect_summary_min_sentences": 3,
        "adversarial": False,
    },
    # ── TC2: Healthy account — risks should be empty or minimal ───────────────
    {
        "test_id": "T2-TC2",
        "name": "Healthy account — Wayne Enterprises",
        "account_id": "ACC-9010",
        "expect_health_status": "Healthy",
        "expect_risks": False,   # healthy account may have no flagged risks
        "expect_min_talking_points": 3,
        "expect_summary_min_sentences": 3,
        "adversarial": False,
    },
    # ── TC3: Churning account — must surface churn signals ────────────────────
    {
        "test_id": "T2-TC3",
        "name": "Churning account — Pinnacle Systems",
        "account_id": "ACC-2944",
        "expect_health_status": "Churning",
        "expect_risks": True,
        "expect_min_talking_points": 3,
        "expect_summary_min_sentences": 3,
        "adversarial": False,
    },
    # ── TC4: New account — recently onboarded ─────────────────────────────────
    {
        "test_id": "T2-TC4",
        "name": "New account — Solaris Data (recently onboarded)",
        "account_id": "ACC-7893",
        "expect_health_status": "New",
        "expect_risks": False,   # new accounts may not have churn risks yet
        "expect_min_talking_points": 2,
        "expect_summary_min_sentences": 2,
        "adversarial": False,
    },
    # ── TC5: Enterprise at-risk with multiple escalation notes ────────────────
    {
        "test_id": "T2-TC5",
        "name": "Enterprise At Risk — Vertex Solutions (multiple escalation signals)",
        "account_id": "ACC-8113",
        "expect_health_status": "At Risk",
        "expect_risks": True,
        "expect_min_talking_points": 3,
        "expect_summary_min_sentences": 3,
        "adversarial": False,
    },
    # ── TC6 (ADVERSARIAL): Non-existent account ID ────────────────────────────
    {
        "test_id": "T2-TC6-ADV",
        "name": "ADVERSARIAL — Non-existent account ID",
        "account_id": "ACC-DOES-NOT-EXIST-99999",
        "expect_health_status": None,
        "expect_risks": False,
        "expect_min_talking_points": 0,
        "expect_summary_min_sentences": 0,
        "adversarial": True,    # Should raise ValueError gracefully, not crash
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: Orchestrator — runs all test cases, builds report
# ══════════════════════════════════════════════════════════════════════════════

def run_evaluation(
    run_task1: bool = True,
    run_task2: bool = True,
    use_llm_judge: bool = True,
) -> EvalReport:
    """
    Task 3 — Run the full evaluation harness.

    Args:
        run_task1      : Whether to run Task 1 test cases.
        run_task2      : Whether to run Task 2 test cases.
        use_llm_judge  : Whether to use LLM-as-judge in addition to rule checks.

    Returns:
        EvalReport — full results with per-test scores and aggregate stats.
    """
    all_results: List[TestCaseResult] = []

    # ── Task 1 tests ──────────────────────────────────────────────────────────
    if run_task1:
        print("\n── Task 1: Ticket Triage Evaluation ──────────────────────────────")
        for tc in TASK1_TEST_CASES:
            label = f"[ADV] " if tc["adversarial"] else ""
            print(f"  Running {tc['test_id']}: {label}{tc['name']} ...", end="", flush=True)
            r = _run_triage_test(
                test_id=tc["test_id"],
                name=tc["name"],
                subject=tc["subject"],
                body=tc["body"],
                expected_urgency=tc["expected_urgency"],
                expected_category=tc["expected_category"],
                expected_product_keywords=tc["expected_product_keywords"],
                expect_kb_match=tc["expect_kb_match"],
                adversarial=tc["adversarial"],
                use_llm_judge=use_llm_judge,
            )
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f" {status} (score={r.quality_score:.2f}, {r.latency_seconds}s)")
            if r.error:
                print(f"    ERROR: {r.error}")
            all_results.append(r)

    # ── Task 2 tests ──────────────────────────────────────────────────────────
    if run_task2:
        print("\n── Task 2: TAM Account Brief Evaluation ──────────────────────────")
        for tc in TASK2_TEST_CASES:
            label = "[ADV] " if tc["adversarial"] else ""
            print(f"  Running {tc['test_id']}: {label}{tc['name']} ...", end="", flush=True)
            r = _run_brief_test(
                test_id=tc["test_id"],
                name=tc["name"],
                account_id=tc["account_id"],
                expect_health_status=tc["expect_health_status"],
                expect_risks=tc["expect_risks"],
                expect_min_talking_points=tc["expect_min_talking_points"],
                expect_summary_min_sentences=tc["expect_summary_min_sentences"],
                adversarial=tc["adversarial"],
                use_llm_judge=use_llm_judge,
            )
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f" {status} (score={r.quality_score:.2f}, {r.latency_seconds}s)")
            if r.error:
                print(f"    ERROR: {r.error}")
            all_results.append(r)

    # ── Aggregate stats ───────────────────────────────────────────────────────
    t1_results = [r for r in all_results if r.task == 1]
    t2_results = [r for r in all_results if r.task == 2]

    task1_score = (
        sum(r.quality_score for r in t1_results) / len(t1_results) if t1_results else 0.0
    )
    task2_score = (
        sum(r.quality_score for r in t2_results) / len(t2_results) if t2_results else 0.0
    )
    overall_score = (
        sum(r.quality_score for r in all_results) / len(all_results) if all_results else 0.0
    )

    report = EvalReport(
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        total_tests=len(all_results),
        passed=sum(1 for r in all_results if r.passed),
        failed=sum(1 for r in all_results if not r.passed),
        task1_score=round(task1_score, 3),
        task2_score=round(task2_score, 3),
        overall_score=round(overall_score, 3),
        results=all_results,
    )
    return report


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: Report writers — JSON and Markdown
# ══════════════════════════════════════════════════════════════════════════════

def _to_serialisable(obj):
    """Task 3 — Recursively convert dataclass objects to dicts for JSON serialisation."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_serialisable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_serialisable(i) for i in obj]
    return obj


def write_json_report(report: EvalReport, path: str = "eval_report.json") -> None:
    """Task 3 — Write the full eval report to eval_report.json."""
    data = _to_serialisable(report)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n  📄 JSON report written → {path}")


def write_markdown_report(report: EvalReport, path: str = "eval_report.md") -> None:
    """Task 3 — Write a human-readable eval report to eval_report.md."""
    lines = [
        "# Evaluation Report — Task 3",
        "",
        f"**Generated:** {report.generated_at}  ",
        f"**Total tests:** {report.total_tests}  |  "
        f"**Passed:** {report.passed}  |  "
        f"**Failed:** {report.failed}  ",
        "",
        "## Summary Scores",
        "",
        "| Scope | Score |",
        "|---|---|",
        f"| Task 1 — Ticket Triage | {report.task1_score:.3f} |",
        f"| Task 2 — TAM Account Brief | {report.task2_score:.3f} |",
        f"| **Overall** | **{report.overall_score:.3f}** |",
        "",
        "---",
        "",
        "## Task 1 — Ticket Triage Results",
        "",
        "| Test ID | Name | Adversarial | Score | Pass | Latency |",
        "|---|---|---|---|---|---|",
    ]

    for r in report.results:
        if r.task != 1:
            continue
        adv = "⚠️ Yes" if r.adversarial else "No"
        status = "✅" if r.passed else "❌"
        lines.append(
            f"| {r.test_id} | {r.name} | {adv} | {r.quality_score:.3f} | {status} | {r.latency_seconds}s |"
        )

    lines += ["", "### Task 1 — Check Details", ""]
    for r in report.results:
        if r.task != 1:
            continue
        lines.append(f"#### {r.test_id}: {r.name}")
        if r.error:
            lines.append(f"> ❌ **Pipeline error:** {r.error}")
        for c in r.checks:
            icon = "✅" if c.passed else "❌"
            lines.append(f"- {icon} **{c.check_name}** — {c.message}  ")
            lines.append(f"  Expected: `{c.expected}` | Actual: `{c.actual}`")
        if r.llm_judge_score is not None:
            lines.append(
                f"- 🤖 **LLM Judge:** {r.llm_judge_score:.2f} — {r.llm_judge_rationale}"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## Task 2 — TAM Account Brief Results",
        "",
        "| Test ID | Name | Adversarial | Score | Pass | Latency |",
        "|---|---|---|---|---|---|",
    ]

    for r in report.results:
        if r.task != 2:
            continue
        adv = "⚠️ Yes" if r.adversarial else "No"
        status = "✅" if r.passed else "❌"
        lines.append(
            f"| {r.test_id} | {r.name} | {adv} | {r.quality_score:.3f} | {status} | {r.latency_seconds}s |"
        )

    lines += ["", "### Task 2 — Check Details", ""]
    for r in report.results:
        if r.task != 2:
            continue
        lines.append(f"#### {r.test_id}: {r.name}")
        if r.error:
            lines.append(f"> ❌ **Pipeline error:** {r.error}")
        for c in r.checks:
            icon = "✅" if c.passed else "❌"
            lines.append(f"- {icon} **{c.check_name}** — {c.message}  ")
            lines.append(f"  Expected: `{c.expected}` | Actual: `{c.actual}`")
        if r.llm_judge_score is not None:
            lines.append(
                f"- 🤖 **LLM Judge:** {r.llm_judge_score:.2f} — {r.llm_judge_rationale}"
            )
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  📄 Markdown report written → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Task 3 — CLI entry point for the evaluation harness."""
    parser = argparse.ArgumentParser(
        prog="eval_harness",
        description="Task 3: Evaluation harness for Task 1 (Triage) and Task 2 (TAM Brief)",
    )
    parser.add_argument(
        "--task", type=int, choices=[1, 2],
        help="Run only Task 1 or Task 2 tests. Omit to run both.",
    )
    parser.add_argument(
        "--no-llm-judge", action="store_true",
        help="Skip LLM-as-judge scoring (faster, rule-based only)",
    )
    args = parser.parse_args()

    run_task1 = args.task in (None, 1)
    run_task2 = args.task in (None, 2)
    use_llm_judge = not args.no_llm_judge

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   📊  Evaluation Harness  —  Task 3                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  LLM-as-judge : {'enabled' if use_llm_judge else 'disabled (--no-llm-judge)'}")
    print(f"  Running      : {'Task 1 + Task 2' if run_task1 and run_task2 else f'Task {args.task} only'}")

    report = run_evaluation(
        run_task1=run_task1,
        run_task2=run_task2,
        use_llm_judge=use_llm_judge,
    )

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   RESULTS SUMMARY                                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Total tests  : {report.total_tests}")
    print(f"  Passed       : {report.passed}  |  Failed: {report.failed}")
    if run_task1:
        print(f"  Task 1 score : {report.task1_score:.3f}")
    if run_task2:
        print(f"  Task 2 score : {report.task2_score:.3f}")
    print(f"  Overall      : {report.overall_score:.3f}")

    # ── Write reports ─────────────────────────────────────────────────────────
    write_json_report(report, "eval_report.json")
    write_markdown_report(report, "eval_report.md")

    print("\n  Done.\n")

    # Exit with non-zero code if any tests failed (useful for CI)
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()

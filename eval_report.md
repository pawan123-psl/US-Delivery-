# Evaluation Report — Task 3

**Generated:** 2026-08-09T13:45:56.034838+00:00  
**Total tests:** 12  |  **Passed:** 12  |  **Failed:** 0  

## Summary Scores

| Scope | Score |
|---|---|
| Task 1 — Ticket Triage | 0.958 |
| Task 2 — TAM Account Brief | 0.921 |
| **Overall** | **0.939** |

---

## Task 1 — Ticket Triage Results

| Test ID | Name | Adversarial | Score | Pass | Latency |
|---|---|---|---|---|---|
| T1-TC1 | P1 — Production pipeline fully down (clear critical case) | No | 0.875 | ✅ | 2.98s |
| T1-TC2 | SSO group mapping — known KB issue | No | 1.000 | ✅ | 1.36s |
| T1-TC3 | Billing — invoice seat count discrepancy (P4) | No | 1.000 | ✅ | 1.38s |
| T1-TC4 | AnalyticsHub dashboard timeout — performance issue | No | 0.875 | ✅ | 1.2s |
| T1-TC5 | Feature request — bulk export in WorkflowEngine | No | 1.000 | ✅ | 1.16s |
| T1-TC6-ADV | ADVERSARIAL — Vague ticket with no product or error code | ⚠️ Yes | 1.000 | ✅ | 2.61s |

### Task 1 — Check Details

#### T1-TC1: P1 — Production pipeline fully down (clear critical case)
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ✅ **urgency_correct** — Urgency should be P1 for this ticket type  
  Expected: `P1` | Actual: `P1`
- ❌ **category_correct** — Category should be Bug  
  Expected: `Bug` | Actual: `Performance`
- ✅ **product_area_relevant** — Product area should reference the correct product/module  
  Expected: `one of ['DataBridge']` | Actual: `DataBridge Pro / Pipelines`
- ✅ **kb_match_as_expected** — KB match found status should match expectation  
  Expected: `kb_match.found=True` | Actual: `kb_match.found=True`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `502 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `290 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

#### T1-TC2: SSO group mapping — known KB issue
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ✅ **urgency_correct** — Urgency should be P2 for this ticket type  
  Expected: `P2` | Actual: `P2`
- ✅ **category_correct** — Category should be Integration  
  Expected: `Integration` | Actual: `Integration`
- ✅ **product_area_relevant** — Product area should reference the correct product/module  
  Expected: `one of ['sso', 'cloudsync', 'securevault', 'authentication']` | Actual: `SecureVault / SSO`
- ✅ **kb_match_as_expected** — KB match found status should match expectation  
  Expected: `kb_match.found=True` | Actual: `kb_match.found=True`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `620 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `360 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

#### T1-TC3: Billing — invoice seat count discrepancy (P4)
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ✅ **urgency_correct** — Urgency should be P4 for this ticket type  
  Expected: `P4` | Actual: `P4`
- ✅ **category_correct** — Category should be Billing  
  Expected: `Billing` | Actual: `Billing`
- ✅ **product_area_relevant** — Product area should reference the correct product/module  
  Expected: `one of ['billing', 'seat', 'invoice']` | Actual: `Billing and Plans`
- ✅ **kb_match_as_expected** — KB match found status should match expectation  
  Expected: `kb_match.found=True` | Actual: `kb_match.found=True`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `527 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `373 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

#### T1-TC4: AnalyticsHub dashboard timeout — performance issue
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ❌ **urgency_correct** — Urgency should be P3 for this ticket type  
  Expected: `P3` | Actual: `P2`
- ✅ **category_correct** — Category should be Performance  
  Expected: `Performance` | Actual: `Performance`
- ✅ **product_area_relevant** — Product area should reference the correct product/module  
  Expected: `one of ['analyticshub', 'analytics', 'dashboard']` | Actual: `AnalyticsHub / Dashboards`
- ✅ **kb_match_as_expected** — KB match found status should match expectation  
  Expected: `kb_match.found=True` | Actual: `kb_match.found=True`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `457 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `332 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

#### T1-TC5: Feature request — bulk export in WorkflowEngine
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ✅ **urgency_correct** — Urgency should be P4 for this ticket type  
  Expected: `P4` | Actual: `P4`
- ✅ **category_correct** — Category should be Feature Request  
  Expected: `Feature Request` | Actual: `Feature Request`
- ✅ **product_area_relevant** — Product area should reference the correct product/module  
  Expected: `one of ['workflowengine', 'workflow']` | Actual: `WorkflowEngine / Core Modules`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `460 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `298 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

#### T1-TC6-ADV: ADVERSARIAL — Vague ticket with no product or error code
- ✅ **all_fields_present** — All TriageOutput fields must be populated  
  Expected: `all required fields non-empty` | Actual: `present`
- ✅ **draft_response_substantive** — Draft response must be a substantive message  
  Expected: `>50 chars` | Actual: `537 chars`
- ✅ **urgency_reasoning_present** — Urgency reasoning must explain the classification  
  Expected: `>20 chars` | Actual: `330 chars`
- ✅ **prompt_version_present** — Prompt version must be echoed in output for auditability  
  Expected: `non-empty` | Actual: `v1.1`

---

## Task 2 — TAM Account Brief Results

| Test ID | Name | Adversarial | Score | Pass | Latency |
|---|---|---|---|---|---|
| T2-TC1 | At-Risk account — Omni Consumer Products ($500k ARR) | No | 0.889 | ✅ | 5.79s |
| T2-TC2 | Healthy account — Wayne Enterprises | No | 1.000 | ✅ | 6.32s |
| T2-TC3 | Churning account — Pinnacle Systems | No | 0.889 | ✅ | 5.18s |
| T2-TC4 | New account — Solaris Data (recently onboarded) | No | 0.857 | ✅ | 5.17s |
| T2-TC5 | Enterprise At Risk — Vertex Solutions (multiple escalation signals) | No | 0.889 | ✅ | 4.61s |
| T2-TC6-ADV | ADVERSARIAL — Non-existent account ID | ⚠️ Yes | 1.000 | ✅ | 0.0s |

### Task 2 — Check Details

#### T2-TC1: At-Risk account — Omni Consumer Products ($500k ARR)
- ✅ **metadata_complete** — AccountBrief must include complete account metadata  
  Expected: `account_id, company, tam, plan_tier all present` | Actual: `account_id=ACC-3336, company=Omni Consumer Products`
- ✅ **executive_summary_length** — Executive summary must be a substantial paragraph (3–5 sentences)  
  Expected: `>=3 sentences` | Actual: `5 sentences`
- ✅ **executive_summary_substantive** — Executive summary must contain meaningful content  
  Expected: `>100 chars` | Actual: `646 chars`
- ✅ **risks_present_for_at_risk_account** — At-risk accounts should have flagged risks  
  Expected: `at least 1 risk` | Actual: `2 risks`
- ✅ **risk_quotes_present** — Every risk must include a direct ticket quote  
  Expected: `all risks have ticket_quote >10 chars` | Actual: `2/2 have quotes`
- ✅ **talking_points_count** — Brief must include actionable talking points for the TAM  
  Expected: `>=3 talking points` | Actual: `3 talking points`
- ✅ **health_status_matches_data** — Health status in brief must match accounts.json record  
  Expected: `At Risk` | Actual: `At Risk`
- ✅ **generated_at_valid_timestamp** — generated_at must be a valid UTC ISO-8601 timestamp  
  Expected: `valid ISO-8601 datetime` | Actual: `2026-08-09T13:45:16.110477+00:00`
- ❌ **output_is_deterministic** — temperature=0.0 must produce identical output for the same input  
  Expected: `same executive_summary on second run` | Actual: `different output`

#### T2-TC2: Healthy account — Wayne Enterprises
- ✅ **metadata_complete** — AccountBrief must include complete account metadata  
  Expected: `account_id, company, tam, plan_tier all present` | Actual: `account_id=ACC-9010, company=Wayne Enterprises`
- ✅ **executive_summary_length** — Executive summary must be a substantial paragraph (3–5 sentences)  
  Expected: `>=3 sentences` | Actual: `5 sentences`
- ✅ **executive_summary_substantive** — Executive summary must contain meaningful content  
  Expected: `>100 chars` | Actual: `507 chars`
- ✅ **talking_points_count** — Brief must include actionable talking points for the TAM  
  Expected: `>=3 talking points` | Actual: `3 talking points`
- ✅ **health_status_matches_data** — Health status in brief must match accounts.json record  
  Expected: `Healthy` | Actual: `Healthy`
- ✅ **generated_at_valid_timestamp** — generated_at must be a valid UTC ISO-8601 timestamp  
  Expected: `valid ISO-8601 datetime` | Actual: `2026-08-09T13:45:26.851890+00:00`
- ✅ **output_is_deterministic** — temperature=0.0 must produce identical output for the same input  
  Expected: `same executive_summary on second run` | Actual: `match`

#### T2-TC3: Churning account — Pinnacle Systems
- ✅ **metadata_complete** — AccountBrief must include complete account metadata  
  Expected: `account_id, company, tam, plan_tier all present` | Actual: `account_id=ACC-2944, company=Pinnacle Systems`
- ✅ **executive_summary_length** — Executive summary must be a substantial paragraph (3–5 sentences)  
  Expected: `>=3 sentences` | Actual: `5 sentences`
- ✅ **executive_summary_substantive** — Executive summary must contain meaningful content  
  Expected: `>100 chars` | Actual: `615 chars`
- ✅ **risks_present_for_at_risk_account** — At-risk accounts should have flagged risks  
  Expected: `at least 1 risk` | Actual: `1 risks`
- ✅ **risk_quotes_present** — Every risk must include a direct ticket quote  
  Expected: `all risks have ticket_quote >10 chars` | Actual: `1/1 have quotes`
- ✅ **talking_points_count** — Brief must include actionable talking points for the TAM  
  Expected: `>=3 talking points` | Actual: `3 talking points`
- ✅ **health_status_matches_data** — Health status in brief must match accounts.json record  
  Expected: `Churning` | Actual: `Churning`
- ✅ **generated_at_valid_timestamp** — generated_at must be a valid UTC ISO-8601 timestamp  
  Expected: `valid ISO-8601 datetime` | Actual: `2026-08-09T13:45:34.350850+00:00`
- ❌ **output_is_deterministic** — temperature=0.0 must produce identical output for the same input  
  Expected: `same executive_summary on second run` | Actual: `different output`

#### T2-TC4: New account — Solaris Data (recently onboarded)
- ✅ **metadata_complete** — AccountBrief must include complete account metadata  
  Expected: `account_id, company, tam, plan_tier all present` | Actual: `account_id=ACC-7893, company=Solaris Data`
- ✅ **executive_summary_length** — Executive summary must be a substantial paragraph (3–5 sentences)  
  Expected: `>=2 sentences` | Actual: `5 sentences`
- ✅ **executive_summary_substantive** — Executive summary must contain meaningful content  
  Expected: `>100 chars` | Actual: `460 chars`
- ✅ **talking_points_count** — Brief must include actionable talking points for the TAM  
  Expected: `>=2 talking points` | Actual: `3 talking points`
- ✅ **health_status_matches_data** — Health status in brief must match accounts.json record  
  Expected: `New` | Actual: `New`
- ✅ **generated_at_valid_timestamp** — generated_at must be a valid UTC ISO-8601 timestamp  
  Expected: `valid ISO-8601 datetime` | Actual: `2026-08-09T13:45:43.209472+00:00`
- ❌ **output_is_deterministic** — temperature=0.0 must produce identical output for the same input  
  Expected: `same executive_summary on second run` | Actual: `different output`

#### T2-TC5: Enterprise At Risk — Vertex Solutions (multiple escalation signals)
- ✅ **metadata_complete** — AccountBrief must include complete account metadata  
  Expected: `account_id, company, tam, plan_tier all present` | Actual: `account_id=ACC-8113, company=Vertex Solutions`
- ✅ **executive_summary_length** — Executive summary must be a substantial paragraph (3–5 sentences)  
  Expected: `>=3 sentences` | Actual: `4 sentences`
- ✅ **executive_summary_substantive** — Executive summary must contain meaningful content  
  Expected: `>100 chars` | Actual: `561 chars`
- ✅ **risks_present_for_at_risk_account** — At-risk accounts should have flagged risks  
  Expected: `at least 1 risk` | Actual: `3 risks`
- ✅ **risk_quotes_present** — Every risk must include a direct ticket quote  
  Expected: `all risks have ticket_quote >10 chars` | Actual: `3/3 have quotes`
- ✅ **talking_points_count** — Brief must include actionable talking points for the TAM  
  Expected: `>=3 talking points` | Actual: `3 talking points`
- ✅ **health_status_matches_data** — Health status in brief must match accounts.json record  
  Expected: `At Risk` | Actual: `At Risk`
- ✅ **generated_at_valid_timestamp** — generated_at must be a valid UTC ISO-8601 timestamp  
  Expected: `valid ISO-8601 datetime` | Actual: `2026-08-09T13:45:51.593772+00:00`
- ❌ **output_is_deterministic** — temperature=0.0 must produce identical output for the same input  
  Expected: `same executive_summary on second run` | Actual: `different output`

#### T2-TC6-ADV: ADVERSARIAL — Non-existent account ID
- ✅ **graceful_error_for_invalid_id** — Invalid account ID should raise ValueError gracefully  
  Expected: `ValueError raised` | Actual: `Account 'ACC-DOES-NOT-EXIST-99999' not found in accounts.json and has no recent tickets. Please verify the account ID.`

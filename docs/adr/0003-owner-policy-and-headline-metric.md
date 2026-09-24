# Owner buckets, security policy, and headline metric

Owner suggestions use a collapsed ~8–12 bucket taxonomy mapped from Kibana Team labels, not the raw ~57-label set. Security Policy rules use narrow vulnerability language only (never the bare word "security" as a default trigger).

## Headline metrics (split eval contract)

Eval uses **two challenge sets** after corpus body fetch:

| Split | Membership | Headline metric |
|-------|------------|-----------------|
| **security_escalation** | `has_security_language` in title+body (SEC-001 patterns) | Missed escalation rate — must output `escalate` |
| **critical_routing** | `impact:critical` without security-language | Owner agreement, urgency agreement, human intervention rate |
| **test** | Temporal holdout | False escalation rate, operational agreement |

Legacy `safety` union (critical OR security-language) remains in split summaries for comparison but is not the primary headline.

## Policy monotonicity

Policy may **raise** urgency or force approval/escalation. Policy must **never downgrade** a classifier `p1` or `escalate` proposal to `p3`/`ask_info`. EMPTY-001 on short bodies preserves high-stakes proposals.

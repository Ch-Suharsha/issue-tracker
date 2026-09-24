# Eval failure diagnosis — issue-triage

Generated after full plan execution (2026-09-21).

## What went wrong initially

The title-only corpus (no bodies) made **100% combined missed escalation** look like total system failure. Three separate issues stacked:

1. **Corpus artifact** — all 5,447 records had empty bodies; EMPTY-001 fired on every combined run.
2. **Metric mismatch** — legacy safety set treated `impact:critical` (team routing priority) the same as security escalation (`escalate` action).
3. **Non-monotonic policy** — EMPTY-001 downgraded Jev `escalate`/p1 proposals to p3/`ask_info` (20 cases in title-only replay).

## Eval progression

| Run | Corpus | Split | Combined missed escalation |
|-----|--------|-------|---------------------------|
| Title-only | no bodies | legacy safety (368) | **100%** |
| Baseline v2 | 99.9% bodies | legacy safety (562) | **61.6%** |
| Post-fix | 99.9% bodies | security_escalation (211) | **0%** |

## Correct product contract (post-fix)

| Split | n | Headline | Combined result |
|-------|---|----------|-----------------|
| **security_escalation** | 211 | Missed escalation | **0%** (0/211) |
| **critical_routing** | 351 | Owner / urgency / approval | 67.5% owner, 4.3% urgency, 98.3% human intervention |
| **test** | 1362 | False escalation | **1.2%** (16/1362) |

## Ablation table (post-fix, Jev classifier)

| Mode | Security missed | Critical owner agree | Test false esc |
|------|-----------------|----------------------|----------------|
| **combined** | **0%** | 67.5% | 1.2% |
| model_only | 97.2% | 67.0% | 1.3% |
| rules_only | 0% | 4.8% | 0% |
| baseline_tfidf | 85.3% | 4.8% | 0% |
| baseline_majority | 100% | 4.8% | 0% |

**Takeaway:** SEC-001 + monotonic EMPTY-001 carry the security contract. Jev alone misses 97% of security-language cases; the policy layer is not optional.

## Representative failure modes (resolved)

### F1 — Policy killed Jev escalate (fixed)

Empty body + Jev `escalate` → EMPTY-001 no longer downgrades. Preserved under monotonic policy.

### F2 — Security product bugs vs escalation (clarified)

`[Security Solution]` functional bugs live in **critical_routing**, not **security_escalation**. They should route at p1 with human approval, not necessarily `escalate`.

### F3 — Title-only blind spots (fixed)

Body fetch surfaced 211 security-language cases (up from 3 title-only). SEC-001 now fires on real vuln text in bodies.

## Manual review notes

- **Security set at 0% missed** is driven by deterministic SEC-001 on pattern match — expected and desired for vuln language.
- **Critical routing** owner agreement ~67% is the next improvement target (Jev routing quality, not escalation).
- **False escalation 1.2%** on test is acceptable; monitor if SEC-001 patterns widen.

## Files

- Baseline v2 (bodies, legacy metric): `data/eval/results/eval_baseline_v2_bodies.json`
- Post-fix: `data/eval/results/eval_postfix_20260921.json`
- Traces: `data/eval/results/trace_eval_20260921T224911Z.jsonl`

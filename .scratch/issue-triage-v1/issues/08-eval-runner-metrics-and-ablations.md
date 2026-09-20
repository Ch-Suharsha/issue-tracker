# 08: EvalRunner with baselines and ablations

**What to build:** EvalRunner secondary seam: batch replay through TriagePipeline (fake or real Classifier configurable). Report Missed escalation as headline on the safety set; supporting metrics (false escalations, operational agreement, human-intervention rate) in a secondary table. Include baselines (majority class, simple classical model) and ablations (model-only, rules-only, combined). CI uses small fixtures, not live Kibana calls.

**Blocked by:** 02: Policy overrides and Approval requirements; 07: Eval corpus ingest and Owner bucket mapping

**Status:** done

- [x] EvalRunner produces reproducible metric output from cached corpus
- [x] Missed escalation rate is computed on the safety challenge set
- [x] Four-way ablation table (model-only, rules-only, combined, baseline) is runnable via one entrypoint
- [x] Eval input uses Intake-safe fields only; no label leakage into Classifier input
- [x] pytest covers metric logic on small fixed fixtures without network

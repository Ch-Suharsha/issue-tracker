# Issue Triage — Project Handoff Document

**Status:** Research and dataset audit complete. No application code built yet.  
**Folder:** `/Users/Checkout/Documents/projects/issue-triage`  
**Written:** 2026-09-19  
**Purpose:** Single source of truth for everything decided, discovered, corrected, still unverified, and where to resume. Any future agent (or human) should be able to answer detailed questions from this file plus the PDFs listed below.

---

## 0. Source materials in this folder

| File | What it is |
|------|------------|
| `claudechat.pdf` (35 pages) | Earlier Claude session: YouTube extraction, project choice (Project 2), six research agents, locked stack proposal, Kibana recommendation, folder naming |
| `codexchat.pdf` (27 pages) | Codex session: FDE handout re-read, corrections to Claude plan, started live Kibana GitHub audit, interrupted by rate/quota limits, began this handoff |
| `tmp/pdfs/fde-handout/handout.txt` + `page-*.png` | Extracted text/images of Aishwarya Srinivasan’s *FDE Portfolio Handout* (9 pages, Sept 2026) |
| `tmp/audit/kibana-impact-audit.jsonl` | **Completed** local audit corpus: closed Kibana issues with impact labels since 2023 (~6,023 unique issues) |
| `tmp/audit/summary.json` | Aggregate counts from the completed audit |
| `tmp/audit/label-timing-sample.json` | Sample of when `impact:*` labels were applied vs issue creation time |
| `Updated to latest.docx`, `I.docx` | Not part of the build plan; ignore unless the user says otherwise |

External references (not stored as files here):

- YouTube: [5 PROJECTS That Will Actually Get You HIRED In 2026](https://youtu.be/Fruw822BMBc) — Aishwarya Srinivasan
- YouTube: [The maturity phases of running evals](https://www.youtube.com/watch?v=FB-MLPhL9Ms) — Phil Hetzel (Braintrust / AI Engineer)
- Handout PDF originally at `~/Downloads/FDE_Portfolio_Handout_Aishwarya_Srinivasan.pdf`
- Evals post (handout page 9): `aishwaryasrinivasan.substack.com/p/ai-evals-explained-for-builders`
- Repo under audit: [`elastic/kibana`](https://github.com/elastic/kibana)

GitHub CLI: authenticated as **Ch-Suharsha** (`gist`, `read:org`, `repo`, `workflow`).

---

## 1. One-sentence project definition

> An AI-assisted **intake-to-resolution workflow** specialized to GitHub issue triage: messy issue text becomes a structured, policy-checked **business action**, humans stay in control, and reliability is proven by replaying real historical issues.

**Not:** a Kibana classifier demo.  
**Not:** a chatbot.  
**Not:** “Project 2 from the handout” as a tutorial clone.

Honest repo/folder name: **`issue-triage`** (not “intake-to-resolution-workflow”).

---

## 2. What the FDE handout says Project 2 is

Source: handout pages 3–4 (`tmp/pdfs/fde-handout/`).

### Real-world problem

Every company has a front door for messy requests (support, IT, security review, HR, vendor onboarding). A human reads each request, interprets it, checks context, decides urgency, and routes it. That work is constant, boring, and inconsistent. Priority mistakes cause SLA / safety failures.

### Explicit workflow (handout)

1. **Request arrives** — form, email, or ticketing API.
2. **Extract structured fields, look up context, classify** — then check policy.
3. **Choose one of four actions:**
   - Ask for missing information  
   - Draft a response  
   - Route to the correct team  
   - Escalate to a human  
4. **Human in the loop:** pause, edit proposed action, approve, resume from same state.
5. **Evaluate** by replaying historical/synthetic tickets; inspect failures by category.

### Handout schema (exact)

```python
class Triage(BaseModel):
    category: str
    urgency: Literal["p1", "p2", "p3"]
    confidence: float
    policy_basis: str
    owner: str
    next_action: Literal["ask_info", "draft_reply", "route", "escalate"]
```

### Handout policy rule (the heart of the project)

> If a security ticket contains a known severity-one signal, escalation must not depend on whether the model happens to reason correctly that day. **Deterministic checks in code, judgment in the model.**

### Handout eval metrics

| Metric | Why it matters |
|--------|----------------|
| Routing accuracy | Did it reach the right team |
| False escalations | Wasted human attention |
| Missed escalations | **The dangerous failure** |
| Tool call success | Integration reliability |
| Human intervention rate | How much the system actually absorbs |

### Handout packaging (pages 7–8)

- One-page discovery brief first (specific fictional customer OK; vague not OK).
- README answers six questions: customer / broken / built / how / eval / change before prod.
- One complete vertical slice; boring stack fine.
- 3-minute demo opening with the business problem + one failure case.
- Build in public.
- Do **not** build all five projects; two done well beat five half-finished.
- Recommended start: Projects 1 + 2; we chose **Project 2 only** as the first build for finishability + network weight.

### LangGraph guidance (verbatim spirit)

If the flow is fixed and simple, ordinary application code is fine. Choosing the smaller abstraction is a senior signal.

---

## 3. How GitHub issues map onto the handout

| Handout concept | Our specialization |
|-----------------|-------------------|
| Incoming request | GitHub issue (title + body) |
| Context lookup | Repo rules, related issues, owner taxonomy (carefully; avoid leakage) |
| Model judgment | Propose category, urgency, owner, next_action, short reasoning |
| Deterministic policy | Security/severity floors, required fields, confidence/automation gates |
| Four actions | `ask_info` / `draft_reply` / `route` / `escalate` |
| Human approval | Workflow checkpoint (separate from escalate) |
| Downstream action | Dry-run: draft comment, propose labels/assignment; never mutate real Kibana |
| Ground truth for eval | Maintainer labels on **closed** historical issues (noisy reference, not perfect truth) |

**Kibana is the evaluation domain and demo dataset — not the product identity.**

---

## 4. Claude’s original plan (summary)

Claude recommended Project 2 first (intake workflow), GitHub-domain version:

1. Ingest closed issues from a large public repo.  
2. One LLM call → typed decision.  
3. Deterministic policy layer overrides on security/severity signals.  
4. Four routes (Claude initially treated “hold for human review” as a fourth *route*).  
5. Human review UI with persisted state.  
6. Replay holdout; headline metric = missed escalations.

### Claude “locked” stack (later challenged by Codex)

| Layer | Claude choice |
|-------|----------------|
| Data | GitHub REST, JSONL cache |
| Model | Gemini 2.0 Flash-Lite |
| Schema | Instructor + Pydantic |
| Backend | FastAPI + SQLAlchemy 2.x + Alembic |
| DB | Neon free Postgres |
| State | Hand-rolled status + `decision_log` |
| Policy | Plain Python functions → `(decision, rule_id, reason)` |
| Eval | pytest + sklearn; MLflow local optional |
| UI | FastAPI + Jinja2 + HTMX |
| Host | Render free + `DEMO_MODE` |

### Claude build order (13 days)

Day 1 ingest → day 2 label mapping → day 3 **baselines before LLM** → day 4 LLM → day 5 policy → day 6 eval → day 7 noise audit → days 8–9 UI → day 10 deploy → day 11 observability/CI → day 12 README → day 13 demo.

### Claude additions from Braintrust talk

1. When hand-labeling/disagreeing, write **justifications**, then cluster into failure categories.  
2. Treat reviewer overrides as a **flywheel** into golden-set v2.

### Claude schema tweaks after reading the handout

- Urgency: three levels `p1/p2/p3` (match handout).  
- Keep **policy basis in deterministic code** (`rule_id` + reason), not as authoritative model output.  
- Add model **reasoning** free-text for the review UI (useful half of `policy_basis`).

---

## 5. Codex corrections — ACCEPTED (do not revert)

The user explicitly accepted Codex’s “recommended corrections” table. These override conflicting Claude assumptions.

### 5.1 Must-change table

| Current (Claude) assumption | Problem | Correction (LOCKED) |
|-----------------------------|---------|---------------------|
| Build a classifier over historical Kibana issues | That is only the **evaluation** component | Build **two connected paths**: (A) live intake→action workflow, (B) offline historical replay harness |
| Four routes include “held for human review” | Human review is a **checkpoint**, not a business action | Business actions = `ask_info`, `draft_reply`, `route`, `escalate`. Separately decide whether an action requires approval |
| “Nothing happens until a human approves” *and* automatic routing | Statements conflict | **Risk matrix:** low-risk actions may auto-execute (or auto dry-run); uncertain/high-impact require approval |
| Model outputs authoritative `policy_basis` | Conflicts with “policy stays outside the model” | Model may emit evidence/reasoning; **code** records authoritative `rule_id`, decision, override reason |
| Model self-reported `confidence` drives automation | LLM confidence is poorly calibrated | Derive review thresholds from **validation performance**, schema validity, consistency, class-specific error rates — not claimed confidence alone |
| Closed-issue labels = perfect ground truth | Labels incomplete, inconsistent, often applied late / with hindsight | Treat as **noisy reference decisions**; run a label-quality audit |
| Temporal split by **closure** date | Decision happens at **arrival** | Split chronologically by **`created_at`**; model sees only intake-time information |
| Stuff “all critical issues” into a 1,000-item sample | Distorts class distribution | **Two evaluations:** naturally distributed operational set + separate critical/safety challenge set |
| `impact:critical` ≡ security/P1 | Product impact ≠ security sensitivity | Evaluate urgency and security escalation **separately** |
| Security keywords “guarantee” safety | Evasion + false positives (“Elastic Security” product name) | Rules force **review or severity floor**; never claim perfect vuln detection |

### 5.2 Three concepts that must stay separate in the data model

1. **Business action (model + policy output)**  
   `ask_info` | `draft_reply` | `route` | `escalate`

2. **Workflow processing state**  
   e.g. `received` → `classified` → `policy_checked` → `awaiting_review` → `approved` → `action_completed` | `failed`

3. **Approval policy**  
   `auto_execute` | `require_approval` | `prohibit_auto`

Mixing these caused Claude’s “four routes including hold-for-review” confusion.

### 5.3 Evaluation restructuring (LOCKED)

Use **three chronological partitions** by `created_at`:

1. **Development set** — inspect freely; design system.  
2. **Validation set** — choose prompts, mappings, rules, thresholds.  
3. **Final test set** — sealed until system is stable.

Score layers separately:

- Schema/structured-output success  
- Category  
- Urgency  
- Owner/routing  
- Action selection  
- Critical-issue recall / missed-escalation rate  
- False-escalation rate  
- Automation coverage vs error rate  
- Human-intervention rate  
- End-to-end action success (dry-run OK)  
- Latency and model cost  

Keep: majority-class + TF-IDF/LogReg baselines; model-only / rules-only / combined ablation.

**Important:** maintainer-label agreement and **policy safety** are different evaluations. A rule that correctly escalates an unlabeled-but-dangerous issue is not automatically a “model error.”

`draft_reply` quality cannot be graded by repo labels — use a small human rubric or start with deterministic templates.

Label-quality audit: independently label a sample with a written rubric + justifications + adjudicate disagreements. Call it a **label-quality audit**, not a mathematical “accuracy ceiling.”

### 5.4 Stack caution (provisional, not over-locked)

Still reasonable:

- FastAPI, Pydantic, SQLAlchemy, PostgreSQL (prefer Neon over Render Postgres), server-rendered HTML (Jinja/HTMX), plain Python policy, no LangGraph for v1.

Probably unnecessary for v1:

- Instructor if the model SDK already does constrained decoding  
- MLflow (versioned JSON/CSV may suffice)  
- Full observability suite on day one (Sentry + structlog + UptimeRobot + Actions all at once)

Reliability work the “15-line state machine” still needs:

- Transactions, idempotency, duplicate-event protection, failure states, retries, optimistic concurrency for reviewers, immutable audit history.

### 5.5 Milestone order (replaces aggressive 1–2 week “everything” estimate)

1. **One complete issue** through intake → classify → policy → review → dry-run action.  
2. Historical ingestion + label-quality audit.  
3. Evaluation + baselines.  
4. Deployment + public demo safety (`DEMO_MODE`).  
5. Failure analysis + portfolio packaging.

Do **not** spend week one only on a giant eval pipeline before a live workflow exists.

### 5.6 What Codex said to keep (unchanged and still correct)

- GitHub issue triage as concrete domain  
- Model judgment ≠ deterministic policy  
- Structured outputs  
- Persist workflow state + audit history  
- Prefer ordinary app code over LangGraph  
- Minimal server-rendered review UI  
- Historical replay + real failure analysis  
- Baselines + missed escalations as primary safety metric  
- Public demo read-only / sandboxed  
- Name: `issue-triage`

---

## 6. Worked examples (keep these for interviews)

### Issue A — empty crash report  
Model: low confidence, `ask_info`.  
System asks for repro. No human time.

### Issue B — README typo  
Model: docs, p3, high confidence, `route`.  
Auto-route (or auto dry-run) to docs.

### Issue C — password-reset link reusable (THE example)  
Model may say p3 routine bug.  
**Policy** sees auth/session language → force `escalate` / p1 regardless of model.  
This is the project’s existence proof.

### Issue D — ambiguous long technical report  
Low automation confidence → require human review checkpoint (workflow state), action may still be `route` after approval.

---

## 7. Kibana dataset audit — COMPLETED FINDINGS

Audit resumed and finished after Codex interruption.

### 7.1 Repo facts (live, 2026-09-19)

- `elastic/kibana` — active, public, not archived  
- ~21.3k stars, ~8.6k forks, ~14.6k open issues reported by API  
- **1,661 labels**  
- Closed issues created since 2023-01-01: **~37,137** (search count)  
- License field: `NOASSERTION` (Elastic License family); issue *text* is public — for portfolio, keep full corpus local; show only a few examples in public demo  
- `SECURITY.md` exists (security vulns go through a disclosure process — do not expect all vulns as public issues)

### 7.2 Official impact label meanings (from GitHub label descriptions)

| Label | Description (verbatim summary) |
|-------|--------------------------------|
| `impact:critical` | Address **immediately** due to critical product impact |
| `impact:high` | High impact on product quality/strength |
| `impact:medium` | Medium impact |
| `impact:low` | Low impact |
| `impact:needs-assessment` | Product/eng still needs to evaluate impact — **not usable as ground truth** |

**Critical implication:** `impact:critical` means “high product impact / address now,” **not** “security incident” and not automatically “P1 security.”

### 7.3 Completed pull (local corpus)

File: `tmp/audit/kibana-impact-audit.jsonl`

| Metric | Value |
|--------|------:|
| Unique closed issues with scored impact labels (created ≥ 2023) | **6,023** |
| `impact:critical` | 434 |
| `impact:high` | 1,897 |
| `impact:medium` | 2,091 |
| `impact:low` | 1,607 |
| Multi-impact labeled issues | 11 |
| PRs accidentally included | 0 in final file (filtered; Codex warned first page of `/issues` was ~31% PRs) |

Year primary-impact distribution (approx):

| Year | critical | high | medium | low | total |
|------|----------|------|--------|-----|-------|
| 2023 | 113 | 438 | 616 | 516 | 1683 |
| 2024 | 114 | 490 | 613 | 384 | 1601 |
| 2025 | 159 | 693 | 524 | 480 | 1856 |
| 2026 (to ~Sep 14) | 48 | 274 | 337 | 224 | 883 |

### 7.4 Noise and filters (required)

| Problem | Evidence | Handling |
|---------|----------|----------|
| CI “Failing test: …” issues | 578 titles in corpus; ~69 critical via search | **Drop** titles starting with `Failing test` |
| QA factory authors `*-qasource` | 1,489 issues in critical+high era; many self-label impact at file time | Keep for volume but document; optionally ablate with/without QA authors |
| “Security” product-name trap | 1,347 usable titles contain “security” | Policy must use **vuln language** (auth bypass, XSS, tenant leak, credential exposure…), **not** the word “security” |
| Deprecated/duplicate teams | e.g. `Team:Fleet - DEPRECATED`; 57 team labels on usable set | Normalize: strip `DEPRECATED`, merge obvious duplicates into ~10–15 owner groups |
| `impact:needs-assessment` | Not a decision | Exclude from scoring labels |
| Category labels sparse | Only ~70.9% of usable issues have bug/enhancement/docs/question | Score category only on labeled subset; don’t pretend 100% coverage |
| Team labels rich | ~98.8% of usable issues have `Team:*` | Good for routing eval after normalization |

**Usable corpus after dropping “Failing test”:** **5,445** issues  
**Usable critical:** **367** → ~25% holdout ≈ **~90 critical** in a natural 75/25 `created_at` split (enough for missed-escalation CIs; far better than rust/k8s).

Rough `created_at` 75/25 split on usable set:

- Dev window: 2023-01-03 → 2025-08-25 (~4083)  
- Test window: 2025-08-26 → 2026-09-14 (~1362)  
- Test critical ≈ 78 in that naive split (still OK); prefer also a **dedicated critical challenge set**.

Joint coverage (category + team) on usable: **~70.2%**.

### 7.5 Label timing / leakage (sampled 36 issues via GraphQL `LABELED_EVENT`)

| When first scored `impact:*` applied | Count (of 36) |
|--------------------------------------|---------------|
| Within 1 minute | 26 |
| Within 1 hour | 2 |
| Within 1 day | 2 |
| Within 1 week | 2 |
| After 1 week (up to months/years) | 4 |

Interpretation:

- Many issues (especially QA-filed) are **self-labeled at creation** — labels are sometimes present at intake.  
- A material minority get impact labels **days to years later** — those labels are hindsight, not intake state.  
- Therefore for **model input**, default to **title + body (+ maybe author type)** only.  
- For **grading**, final impact/team/category labels are a **noisy reference** of eventual maintainer judgment — not “what a triager knew at t=0.”  
- Details: `tmp/audit/label-timing-sample.json`.

### 7.6 Qualitative read of “critical”

Recent non-failing critical titles include:

- Real production pain (OOM on prebuilt rules, dashboard won’t open, cross-space entity visibility)  
- Security *product* bugs (Security Solution UI/API failures) — product area, not necessarily vuln class  
- Roadmap / “as code” API work labeled critical  
- Accessibility / UX defects occasionally  

So: **critical ≠ security P1**. Map:

| Kibana label | Our urgency field (operational mapping) | Notes |
|--------------|----------------------------------------|-------|
| `impact:critical` | `p1` candidate for **impact urgency** | Not automatic security escalate |
| `impact:high` | `p2` | |
| `impact:medium` / `impact:low` | `p3` | |
| Security vuln language in text / known patterns | Policy may force escalate | Separate axis from impact |

### 7.7 Preliminary recommendation on Kibana

**Use `elastic/kibana` as the primary evaluation corpus**, with mandatory filters and dual eval sets.

Reasons it wins vs alternatives:

- Only candidate with **hundreds** of critical-impact closed issues since 2023 after filtering.  
- Clear ordinal impact scale with official descriptions.  
- Extremely high `Team:*` coverage for routing experiments.  
- Readable product-bug titles for demos.

Reasons it is **not** “clean ground truth”:

- Impact ≠ security.  
- Heavy QA/CI noise.  
- “Security” token pollution.  
- Team taxonomy sprawl + deprecations.  
- Late labels → leakage risk if mishandled.  
- Category labels incomplete.

**Do not treat raw Kibana labels as unquestioned ground truth.** Kibana is usable after filtering + label-quality audit + separate safety eval.

---

## 8. Alternative repository comparison

Live search counts (closed issues, created ≥ 2023-01-01), 2026-09-19:

| Repo | Severity taxonomy | “Top” severity count | All scored severity (approx) | Verdict |
|------|-------------------|----------------------|------------------------------|---------|
| **elastic/kibana** | `impact:critical/high/medium/low` | **434** critical | ~6.0k with any impact | **Primary pick** |
| rust-lang/rust | `P-critical/high/medium/low` | 110 critical | ~747 with any P-* | Too few critical for sturdy missed-escalation CI; compiler jargon hurts demos |
| kubernetes/kubernetes | `priority/critical-urgent` etc. | 113 critical-urgent | thinner; lots of CI/sig noise | Weak critical volume; security via `area/security` (~48) separate |
| grafana/grafana | `prio/critical` (note spelling) | **6** | essentially unusable for severity eval | Reject for severity grading |
| prometheus/prometheus | `priority/P0`… | P0≈0, P1≈12 | Too small | Reject |

**Conclusion:** No alternative beats Kibana on measurable critical volume + ordinal severity + owner labels. If Kibana were abandoned, rust-lang/rust is second — but expect weak safety-metric statistics.

---

## 9. Proposed evaluation design (concrete)

### 9.1 Ingest filters (v1)

Include closed issues from `elastic/kibana` where:

- `created_at >= 2023-01-01`  
- Has exactly one preferred impact label among critical/high/medium/low (if multi, take highest severity and log)  
- Not a PR  
- Title does **not** start with `Failing test`  
- Optionally flag `author` ending in `-qasource` for ablation  

Cache immutable raw JSONL on disk; Postgres holds **live workflow state only**.

### 9.2 Two eval sets

1. **Operational set** — natural class mix; temporal `created_at` splits (dev / val / test).  
2. **Safety challenge set** — all usable critical + hand-picked security-language cases (even if not labeled critical); measure missed escalations / forced-review recall.

### 9.3 Model I/O

**Input (intake-safe):** title, body, optional author_type.  
**Not input:** final labels, comments, assignees, closed_at, later timeline.

**Model output (proposed):**

```text
category, urgency (p1|p2|p3), owner_suggestion, next_action,
reasoning (short), observed_signals (optional list)
```

**Not authoritative from model:** policy decision / rule_id.

### 9.4 Policy layer examples

- `SEC-001` vuln-language → escalate + require approval (not mere “security” substring)  
- Severity floor: if model says p3 but rules fire → escalate  
- Empty/short body → force `ask_info`  
- Schema invalid → fail state / retry / hold for review  
- Automation gate from **validation metrics**, not raw confidence  

### 9.5 Risk matrix (approval policy)

| Situation | Approval policy |
|-----------|-----------------|
| High-confidence docs typo → `route` | `auto_execute` (dry-run in public demo) |
| `ask_info` with clear missing repro | `auto_execute` comment draft |
| `escalate` or p1 | `require_approval` |
| Low validation score / invalid schema | `require_approval` or `prohibit_auto` |
| Public portfolio URL | All writes no-op under `DEMO_MODE`; serve seeded/precomputed results |

---

## 10. Product decisions still needed before coding

These were flagged by Codex and remain open (user should answer when starting build):

1. Hypothetical customer + real user of the review UI (e.g. “maintainer triager” vs “support lead”).  
2. Volume/pain numbers — invent only if clearly labeled fictional (handout-style discovery brief).  
3. Which actions may auto-execute in the private demo vs public demo.  
4. Exact owner taxonomy mapping (collapse 57 teams → ~10–15).  
5. What “resolution” means here (we triage; humans resolve — keep naming honest).  
6. Live intake mechanism for demo: web form, paste issue URL, import by number, and/or webhook simulation.  
7. Safe action target: controlled throwaway repo or dry-run log — **never** write to elastic/kibana.  
8. Whether `draft_reply` is template-based in v1 (recommended) or free-form LLM.

---

## 11. Stack recommendation (current, provisional)

| Layer | Choice | Status |
|-------|--------|--------|
| Language | Python 3.11+ | Likely |
| API | FastAPI | Likely |
| DB | Neon Postgres (not Render Postgres) | Likely — Render free DB deletes ~44 days |
| ORM | SQLAlchemy 2.x + Alembic | Likely |
| UI | Jinja2 + HTMX (single service) | Likely |
| LLM | Re-verify free tier at build time (Claude had Gemini Flash-Lite) | **Must re-check quotas** |
| Structured out | Native SDK schema and/or Pydantic validation | Prefer simplest that raises catchable errors |
| Policy | Plain functions + pytest | Locked |
| Eval | pytest + sklearn; JSON/CSV run logs | Locked direction |
| Host | Render web + Neon DB + `DEMO_MODE` | Likely |
| Orchestration | No LangGraph v1 | Locked |
| Queue | None v1; `asyncio` semaphore for batch replay | Locked |

---

## 12. What was started but unfinished (Codex) — NOW UPDATED

| Task | Codex status | Status after this handoff |
|------|--------------|---------------------------|
| Medium/low impact pull | Interrupted | **Done** — full 6,023 corpus |
| Category/owner coverage | Incomplete | **Done** — see §7.4 |
| Label consistency over years | Incomplete | **Partially done** — yearly impact counts stable enough; deeper taxonomy drift still optional |
| `created_at` temporal design | Recommended | **Adopted** |
| Dual eval sets | Recommended | **Adopted** |
| Alternatives comparison | Not finished | **Done** — Kibana remains best |
| `handout.md` | Started, not written | **This file** |
| Application code / ingest script | Not started | **Not started** |
| Label-quality audit (human 50) | Not started | **Not started** |
| Discovery brief | Not started | **Not started** |

### Still optional / not fully verified

1. Broader label-timing study (n=36 sample only).  
2. Systematic multi-label conflict rate beyond 11 cases.  
3. Full deprecated-team merge map.  
4. Comment leakage experiment (prove accuracy drops when comments excluded — expected).  
5. Re-verify Gemini/other free-tier arithmetic on build day.  
6. Read Aishwarya’s evals Substack post before writing the eval README section.  
7. Confirm Elastic licensing stance for quoting issue text in a public README (prefer minimal quotes).

---

## 13. Exact resume point for the next coding session

**Do this next, in order:**

1. Confirm with the user: **proceed with Kibana** under the filters in §9.1 (recommended: yes).  
2. Write a one-page **discovery brief** in `docs/discovery-brief.md` (fictional but specific).  
3. Write `CLAUDE.md` / `AGENTS.md` pointing at this `handout.md` so future sessions load context.  
4. Implement **Milestone 1** — not the full ingest yet if it delays the vertical slice:
   - Minimal FastAPI app  
   - Paste or select one issue (can hardcode a fixture from the JSONL)  
   - One LLM classify call (or stub) → structured object  
   - One policy function (security-language rule)  
   - Review page: edit/approve  
   - Dry-run action logger  
   - `decision_log` row in Postgres (or SQLite for day-1 if Neon not ready)  
5. Then Milestone 2: productionize ingest from `tmp/audit/kibana-impact-audit.jsonl` (or re-pull with richer fields: full body text — current audit stores `body_chars` only!).  

### Critical data gap for coding

The audit JSONL stores **`body_chars` but not body text**. For training/eval/LLM calls you must either:

- Re-fetch issue bodies for the sampled IDs, or  
- Extend the ingest script to store `body` (and maybe truncate in gitignored data files).

Do **not** commit full issue bodies to a public GitHub repo.

---

## 14. Interview / README narrative (ready-made)

**Problem:** Maintainer teams drown in inconsistently triaged issues; security-relevant reports can look polite and routine.

**What we built:** An intake workflow that proposes a structured action, applies deterministic policy overrides, requires human approval on high-impact paths, and dry-runs the operational action.

**How we know it works:** We replay filtered historical Kibana issues with temporal holdouts, baselines, ablations, and a safety challenge set focused on missed escalations — with raw counts, not vanity accuracy.

**Key design judgment:** The model never gets the final word on mandatory escalations (Issue C story).

**Honest limitation:** Maintainer impact labels are noisy and are not security labels; we audited that and designed metrics accordingly.

---

## 15. Chronology of decisions (compressed)

1. Watched FDE projects video → chose easier meaningful project → Claude: Project 2.  
2. Six research agents → Claude stack lock + Kibana lean.  
3. Braintrust eval talk → justifications + review flywheel.  
4. Read FDE handout → schema/urgency alignment; policy stays outside model.  
5. Clarified mental model: four **actions**, not four categories.  
6. Live label counts → Kibana over rust/k8s.  
7. Moved work to `projects/issue-triage`.  
8. Codex re-read handout → corrected classifier-vs-workflow mistake; accepted corrections.  
9. Codex Kibana audit started; quota interrupted.  
10. **This session:** finished audit, compared alternatives, wrote this handoff.

---

## 16. Files the next agent should create first

```text
handout.md              ← (this file; already done)
docs/discovery-brief.md
AGENTS.md or CLAUDE.md  ← pointer + non-negotiables
.gitignore              ← data/, .env, bodies cache
src/ ...                ← only after Milestone 1 scope agreed
```

---

## 17. Non-negotiables (checklist)

- [ ] Output is a **decision/action**, not chat text  
- [ ] Model proposes; **code + humans** dispose  
- [ ] Business action ≠ workflow state ≠ approval policy  
- [ ] Missed escalations are the safety headline  
- [ ] Live workflow path exists, not only offline classification  
- [ ] Public demo cannot burn API keys or corrupt data (`DEMO_MODE`)  
- [ ] No writes to `elastic/kibana`  
- [ ] Eval input = intake-time fields only  
- [ ] Dual eval sets (operational + safety)  
- [ ] Baselines before claiming LLM value  
- [ ] Name stays `issue-triage`

---

*End of handoff. If anything in §10 is unanswered, ask the user before inventing product claims.*

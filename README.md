# Issue Triage

AI-assisted **Triage** (not Resolution) for messy GitHub Issues: one structured model proposal, deterministic policy overrides, human approval on high-impact paths, and dry-run actions only — never writes to elastic/kibana.

Built as an FDE portfolio proof. Evaluation replays filtered public Kibana Issues offline; the product identity is the workflow, not “a Kibana classifier.”

---

## Evaluation — headline metric

**Missed escalation** (safety challenge set): share of cases that should have escalated (or forced approval on a critical path) but did not.

Run `uv run eval` to generate metrics (EvalRunner — ticket 08). Example output format:

| Metric | Safety set | Operational set |
|--------|------------|-----------------|
| **Missed escalation** | **TBD** | — |
| False escalation rate | TBD | TBD |
| Routing agreement (bucket) | — | TBD |
| Urgency agreement | — | TBD |
| Human intervention rate | TBD | TBD |

Supporting table (baselines & ablations — placeholder until eval ships):

| System | Missed escalation (safety) | Notes |
|--------|----------------------------|-------|
| Majority class baseline | TBD | Always `route` / p3 |
| Classical baseline | TBD | TF-IDF + logistic |
| Model only | TBD | No policy layer |
| Policy only | TBD | Rules without LLM |
| **LLM + policy (v1)** | **TBD** | Shipped system |

Ground truth is **noisy**: maintainer labels on closed Issues are reference decisions, often applied late or with hindsight. We report agreement and safety separately.

---

## Six questions (FDE handout)

### 1. Customer — who is this for?

A **fictional** six-person open-source maintainer team (Kibana-shaped). See [docs/discovery-brief.md](docs/discovery-brief.md). Recruiters evaluating embedded-engineering skill are the real audience.

### 2. What was broken?

~100–150 Issues/week, inconsistent urgency and ownership, high-impact reports sitting in `needs-triage`, no structured audit trail. Triage is manual, boring, and error-prone on safety-sensitive language.

### 3. What we built

- **Intake:** paste form (title + body) or GitHub import by issue number/URL.
- **TriagePipeline:** one Classifier call → Policy rules → Approval policy → optional dry-run record.
- **Business actions:** `ask_info`, `draft_reply`, `route`, `escalate` (templates, not free-form LLM replies).
- **Review UI:** FastAPI + Jinja; approve/reject with optimistic concurrency.
- **Persistence:** SQLAlchemy workflow row + decision log (SQLite local, Neon Postgres in production).
- **Public demo:** `DEMO_MODE` + seeded Issues on first load.

### 4. How it works

```
Issue (title, body) → Classifier proposal → Policy (deterministic overrides)
  → Approval policy → [human checkpoint] → Dry-run action (DB only)
```

Policy runs **after** the model and can override urgency, owner, and action. Security rules match **vulnerability language** (e.g. password reset, auth bypass), not the bare word “security” (Elastic Security product noise).

### 5. How we evaluate

- **Dual sets:** operational (natural mix, temporal split by `created_at`) + safety challenge (must-escalate cases).
- **Intake-safe inputs only** — no comment/label leakage at classification time.
- **Headline:** missed escalation on the safety set.
- Offline replay via EvalRunner; CI uses small fixtures, not live GitHub in every run.

### 6. What would change before production?

| Area | v1 portfolio | Production |
|------|--------------|------------|
| Classifier | `FakeClassifier` by default; **Jev** when `TYPESAFE_API_KEY` is set | Provider swappable behind Classifier port |
| Host | Render free + Neon + `DEMO_MODE` | Private deploy, SSO, rate limits |
| Actions | Dry-run only | Customer-approved integrations (still not blind write to upstream) |
| Eval flywheel | Static corpus | Reviewer overrides → golden set v2 |
| Observability | `/health` + decision log | Metrics, tracing, alert on policy override rate |

---

## Failure analysis (honest)

### Issue C — policy override (password reset)

**Input:** Reporter says a password-reset link works twice; session/auth language in the body.

**Model (FakeClassifier):** p3, `route` — “routine bug.”

**Policy SEC-001:** vulnerability-language match → force **p1**, **escalate**, Security owner.

**Why it matters:** Escalation must not depend on the model having a good day. This is the existence proof for the policy layer.

Try it: open the seeded “Password reset link still works…” issue in demo mode and read the policy badge on the review page.

### Label noise

We score against maintainer labels on **closed** Kibana Issues, but:

- `impact:critical` means product impact, not security P1.
- Labels are often applied at closure, not at arrival.
- ~11% of audited Issues carry conflicting impact labels.

We treat labels as **noisy reference**, not ground truth. Agreement metrics are reported separately from policy safety.

### Security word trap

A naive rule that escalates on the substring `"security"` would fire constantly on “Elastic Security” product Issues. v1 rules match **vulnerability patterns** only (`password reset`, `auth bypass`, `xss`, etc.). Residual risk: evasion and false negatives — we measure missed escalation rather than claiming perfect detection.

---

## Try the demo

**Live app:** [https://issue-triage.onrender.com](https://issue-triage.onrender.com) — full workflow with **Jev** (TypeSafe) classifier. Submit an issue or import from GitHub. See [docs/deploy.md](docs/deploy.md).

| Mode | Where | Classifier |
|------|-------|------------|
| Production | Render + Neon | Jev (`TYPESAFE_API_KEY`) |
| Read-only demo | Local `DEMO_MODE=true` | FakeClassifier (seeded) |

Architecture: **FastAPI + Jinja** (not Streamlit). One Python web service, Neon Postgres, no cron.

**Local (full workflow):**

```bash
uv sync
uv run issue-triage          # http://127.0.0.1:8000
# or: uv run uvicorn issue_triage.app:create_app --factory --reload
```

Submit the form with “Typo in README” or import a public Issue (e.g. `elastic/kibana#12345`).

**Public-style (read-only):**

```bash
export DEMO_MODE=true
uv run uvicorn issue_triage.app:create_app --factory --host 0.0.0.0 --port 8000
```

First load seeds three examples if the database is empty. Intake and approve are disabled; browse seeded rows and open **Password reset…** for the policy override story.

Deploy (~10 min, $0): [docs/deploy.md](docs/deploy.md) · [Alternatives](docs/deploy-alternatives.md)

---

## Development

```bash
uv sync
uv run pytest
cp .env.example .env   # optional local overrides
```

Key env vars: `DATABASE_URL`, `DEMO_MODE`, `TYPESAFE_API_KEY` (enables Jev) — see [.env.example](.env.example).

### Classifier (Jev / TypeSafe)

By default the app uses `FakeClassifier` (no API key, deterministic demos). Set `TYPESAFE_API_KEY` to triage with [TypeSafe Jev](https://docs.typesafe.ai/introduction) — structured Choice answers for category, urgency, owner bucket, and business action. Policy (SEC-001, EMPTY-001) still runs in Python after Jev. `DEMO_MODE=true` always uses FakeClassifier. Optional `JEV_MIN_CONFIDENCE=0.5` forces human approval when Jev is uncertain.

---

## Scope boundaries

- **Triage ≠ Resolution** — no code fixes, no closing Issues as fixed.
- **No writes to elastic/kibana** in any environment.
- **No LangGraph** in v1 — workflow code is the source of truth.
- Kibana is the **eval domain**, not the product name.

Docs: [CONTEXT.md](CONTEXT.md) · [ADRs](docs/adr/) · [Discovery brief](docs/discovery-brief.md)

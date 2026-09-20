# Deploying issue-triage (Render + Neon)

Deploy the **existing FastAPI + Jinja app** — no Streamlit rewrite, no cron jobs. See [deploy-alternatives.md](deploy-alternatives.md) for why.

Two profiles:

| Profile | Purpose | Classifier | `DEMO_MODE` |
|---------|---------|------------|-------------|
| **A — Public demo** | Recruiter URL, seeded examples | FakeClassifier (forced) | `true` |
| **B — Live Jev** | Full intake + real triage | Jev (TypeSafe) | `false` |

Use **separate Neon databases** for A and B. Never share one DB between public demo and live production.

---

## Prerequisites

- [Render](https://render.com) account (free web service tier)
- [Neon](https://neon.tech) account (free Postgres tier)
- GitHub repo pushed (e.g. `Ch-Suharsha/issue-tracker`)

---

## Profile A — Public portfolio demo (deploy this first)

### 1. Neon Postgres

1. Create a Neon project and database (demo DB).
2. Copy the **pooled** connection string (`postgresql://...?sslmode=require`).
3. Paste into Render env vars only — never commit to git.

SQLAlchemy accepts Neon URLs as `DATABASE_URL` with no code changes.

### 2. Render web service

**Option A — Blueprint (recommended):** Connect the repo and apply [`render.yaml`](../render.yaml) at the repo root.

**Important:** After blueprint apply, open the Render dashboard and set `DATABASE_URL` manually (`sync: false` in the blueprint). The deploy will not work until Neon URL is pasted.

**Option B — Manual:**

| Setting | Value |
|---------|--------|
| Build command | `curl -LsSf https://astral.sh/uv/install.sh \| sh && export PATH="$HOME/.local/bin:$PATH" && uv sync` |
| Start command | `uv run uvicorn issue_triage.app:create_app --factory --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

### 3. Environment variables (Render dashboard)

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Neon pooled Postgres URL (demo DB) |
| `DEMO_MODE` | `true` |
| `PYTHON_VERSION` | `3.11` |

**Do not set on public demo:** `TYPESAFE_API_KEY`, `GITHUB_TOKEN`, or any API keys.

### 4. First deploy behavior (no cron)

On startup the app automatically:

1. Creates tables if missing (`init_db`).
2. Seeds **three demo issues** when the workflow table is empty ([`seed.py`](../src/issue_triage/seed.py)):
   - README typo (auto dry-run)
   - Password reset (SEC-001 policy override, awaiting approval)
   - Empty body (EMPTY-001 ask_info)
3. Serves the home page; mutating routes return 403 in `DEMO_MODE`.

No cron job or background worker is required — seeding runs once per empty database on boot.

### 5. Verify Profile A

```bash
curl https://<your-service>.onrender.com/health
# → {"status":"ok","demo_mode":true}
```

Browser checks:

- Home page lists 3 seeded issues
- Intake/approve buttons disabled
- Open **Password reset link still works…** → policy badge **SEC-001**

### 6. Render free tier notes

- Service **spins down after ~15 minutes idle** — first visit after idle may take ~30–60s (cold start).
- Neon free tier has storage/compute limits — fine for portfolio demo traffic.
- **Total cost: $0** for Profile A.

---

## Profile B — Production with live Jev (optional)

Use when you want real intake, GitHub import, and Jev classification (`Jev: category=... (conf 0.xx)` in reasoning).

### Setup

| Setting | Value |
|---------|--------|
| Host | **Second** Render service, or local `./scripts/run.sh` |
| DB | **Separate** Neon branch/database (not the demo DB) |
| `DEMO_MODE` | `false` |
| `TYPESAFE_API_KEY` | From [TypeSafe console](https://console.typesafe.ai) |
| `TYPESAFE_MODEL` | Optional; default `jev-latest` |
| `JEV_MIN_CONFIDENCE` | Optional (e.g. `0.5`) — low confidence forces human approval |
| `GITHUB_TOKEN` | Optional — GitHub import rate limits |

When `TYPESAFE_API_KEY` is set and `DEMO_MODE=false`, [`classifier_factory.py`](../src/issue_triage/classifier_factory.py) selects `JevClassifier` automatically.

### Safety warnings

- **Do not** expose Profile B on a public URL without access control — anonymous users can burn TypeSafe API quota.
- Prefer: keep URL private, password-protect, or run locally for live Jev demos.
- **Never** set `TYPESAFE_API_KEY` on Profile A (public demo).

### Local Profile B

```bash
cp .env.example .env
# DATABASE_URL=sqlite:///./dev.db   # or Neon prod branch URL
# DEMO_MODE=false
# TYPESAFE_API_KEY=...
./scripts/run.sh
```

---

## 3-minute recruiter demo script (Profile A)

1. Open live URL → show **Recent issues** (3 seeded rows).
2. Open **Typo in README** → auto dry-run, no approval (low-risk path).
3. Open **Password reset link still works…** → **SEC-001** policy badge, p1 escalate — “policy overrides the model.”
4. Mention: “Live Jev classifier available on private instance; public demo is read-only for safety.”

---

## Local production-like check (Profile A)

```bash
cp .env.example .env
# DATABASE_URL=...  (Neon or sqlite)
export DEMO_MODE=true
./scripts/run.sh
```

Open http://127.0.0.1:8000 — seeded issues appear; intake disabled.

---

## FAQ

### Why not Streamlit?

The app is **FastAPI + Jinja/HTMX** ([`app.py`](../src/issue_triage/app.py), [`web_templates/`](../src/issue_triage/web_templates/)). Streamlit would be a full UI rewrite with no spec backing. Deploy as-is on Render.

### Why not store workflow in GitHub?

Workflow state and audit logs live in **Postgres** ([`repository.py`](../src/issue_triage/repository.py)). GitHub is import-only (fetch title/body at intake time).

### Do I need a cron job?

No. [`seed_if_empty()`](../src/issue_triage/seed.py) runs on application startup when the DB is empty.

### Intake returns 403 on public demo

Expected when `DEMO_MODE=true`. Profile A is read-only by design.

### Empty home page after deploy

- Check `DATABASE_URL` is set and reachable (Neon pooled URL with `sslmode=require`).
- Check Render logs for startup errors.
- Hit `/health` first.

### Classifier failures (`status=failed`)

On Profile B, API errors land as `failed` status with a message on the review page — not a 500. Check `TYPESAFE_API_KEY` and TypeSafe billing.

---

## Out of scope for v1 deploy

- Writing to elastic/kibana (never enabled)
- Render free Postgres (use Neon per ADR 0004)
- Streamlit or separate frontend rewrite
- Cron-based seeding or background workers

See also: [deploy-alternatives.md](deploy-alternatives.md)

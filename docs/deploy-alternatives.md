# Deploy alternatives (why Render + Neon)

This doc records the deployment decision after grilling the Streamlit rewrite proposal. **Recommendation: deploy the existing app on Render + Neon.**

## Comparison

| Option | Fits current code? | Rewrite needed? | Free tier | Verdict |
|--------|-------------------|-----------------|-----------|---------|
| **Render + Neon** | Yes — `render.yaml` exists | None | Yes | **Use this** |
| Streamlit Community Cloud | No Streamlit in repo | Full UI + app shell | Yes | Rejected |
| Railway / Fly.io | Yes — same uvicorn start | None | ~$0 / trial | OK but no blueprint |
| Vercel serverless | Poor fit | Major | Yes | Rejected — long-lived FastAPI + SQLAlchemy |
| GitHub as database | No | New persistence layer | — | Rejected — Postgres already wired |

## Why Streamlit was rejected

- Locked v1 architecture: one FastAPI web service, server-rendered HTML (ADR 0004).
- UI already built: forms, review page, approve/reject, policy badges, dry-run display.
- GitHub does not replace Neon for workflow state, optimistic concurrency, or decision logs.
- Public demo safety comes from `DEMO_MODE` + FakeClassifier, not from the hosting platform.
- `render.yaml` and [deploy.md](deploy.md) already document the ship path.

## When Streamlit might make sense

A **new** internal analytics dashboard or scratch prototype — not for this triage workflow, which is form-based with human approval gates and policy overrides.

## Recommended path

1. **Profile A:** Render free + Neon free + `DEMO_MODE=true` — public portfolio URL.
2. **Profile B (optional):** Second service or local + `TYPESAFE_API_KEY` — live Jev triage.

See [deploy.md](deploy.md) for step-by-step instructions.

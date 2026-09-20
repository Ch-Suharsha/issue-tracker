# 09: DEMO_MODE, deploy, and seeded public demo

**What to build:** Public-safe demo: DEMO_MODE no-ops mutating paths, avoids unbounded live LLM spend on anonymous visitors, and serves seeded example Issues so a cold visit is populated. Deploy the web app (Render) with Neon Postgres; verify the portfolio URL loads and demonstrates Triage without corrupting data.

**Blocked by:** 04: Form intake → review → approve → dry-run (first vertical slice); 06: Template replies and balanced auto-proceed

**Status:** done

- [x] DEMO_MODE blocks or no-ops writes with a friendly message
- [x] Public demo can show precomputed or seeded results without burning API quota
- [x] App deploys with working health/read path and persisted demo seed data
- [x] Tests assert DEMO_MODE mutating paths are safe
- [x] No writes to elastic/kibana in any environment

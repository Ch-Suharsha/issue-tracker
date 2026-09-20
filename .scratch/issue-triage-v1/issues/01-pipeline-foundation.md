# 01: TriagePipeline foundation with fake Classifier

**What to build:** Scaffold with `uv init` first, then add any extra directories the layout needs, then add code. Deliver a runnable Python project with pytest, the TriagePipeline primary seam, and a swappable Classifier port backed by a fake in tests. Given an Issue (title and body), the pipeline returns a structured proposal (category, urgency, Owner bucket, Business action, reasoning) without calling a real LLM or starting a web server.

**Blocked by:** None (can start immediately)

**Status:** done

**Scaffold order:** `uv init` → create `src/` / `tests/` (and any other dirs) → add dependencies via `uv add` → implement pipeline + tests.

- [x] Project initialized with `uv init`; dependencies managed with uv (`pyproject.toml` + lockfile)
- [x] pytest runs green with no network or API keys required
- [x] TriagePipeline accepts Issue input and returns a typed structured proposal
- [x] Classifier is behind a port; tests inject a deterministic fake
- [x] No LangGraph; workflow logic lives in ordinary application code

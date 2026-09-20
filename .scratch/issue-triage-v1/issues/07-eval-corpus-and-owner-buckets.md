# 07: Eval corpus ingest and Owner bucket mapping

**What to build:** Offline ingest for the Eval corpus: filtered elastic/kibana closed Issues (created since 2023, no PRs, drop "Failing test" titles). Cache raw records locally (gitignored bodies). Define ~8–12 Owner buckets and mapping from Kibana Team labels. Build operational and safety eval splits by `created_at` with documented counts per class.

**Blocked by:** 01: TriagePipeline foundation with fake Classifier

**Status:** done

- [x] Ingest script caches corpus locally; full bodies are not committed to the public repo
- [x] Filters match spec (Failing test excluded, intake-safe fields documented)
- [x] Owner bucket taxonomy and Team label mapping table exist and are documented
- [x] Operational and safety challenge splits are reproducible with per-class counts reported

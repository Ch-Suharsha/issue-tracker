# 05: GitHub import Intake

**What to build:** Second Intake path: import a public GitHub Issue by number or URL (elastic/kibana or any public repo). Fetch title and body only at Intake time — no comments, final labels, or later timeline as model input. Imported Issues enter the same TriagePipeline and review flow as form paste.

**Blocked by:** 04: Form intake → review → approve → dry-run (first vertical slice)

**Status:** done

- [x] Triager can import by issue number or URL and land in the same review flow
- [x] Only Intake-safe fields are stored and passed to the Classifier
- [x] Import is idempotent or deduplicated where practical on retry
- [x] Failure to fetch shows a clear error without corrupting workflow state

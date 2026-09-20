# 03: Postgres workflow state and decision log

**What to build:** Persist each Issue's workflow through Triage in Postgres (Neon locally): workflow status, proposal fields, Approval state, and an immutable decision log for every transition. TriagePipeline writes proposal, policy result, approval requirement, and log entries transactionally. Triager updates use optimistic concurrency so two reviewers cannot silently overwrite each other.

**Blocked by:** 02: Policy overrides and Approval requirements

**Status:** done

- [x] Workflow row survives restart; status is the resume point
- [x] decision_log records what changed, which Policy rule fired, and why
- [x] Business action, workflow status, and Approval policy remain separate fields
- [x] Bad model/schema output lands in a safe failure or hold path, not an undefined state
- [x] Integration tests cover persist → reload → continue from same state

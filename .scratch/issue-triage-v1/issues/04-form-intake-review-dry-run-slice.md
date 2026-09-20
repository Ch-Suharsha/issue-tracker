# 04: Form intake → review → approve → dry-run (first vertical slice)

**What to build:** The first complete product path: FastAPI + server-rendered UI (Jinja/HTMX). A Triager pastes title and body, the system runs TriagePipeline (real Classifier allowed in dev), shows the proposal with Policy rule badge, pauses for Approval when required, lets the Triager edit and approve or reject, and records a Dry-run action (intended comment, labels, assignment) without writing to elastic/kibana.

**Blocked by:** 03: Postgres workflow state and decision log

**Status:** done

- [x] Form Intake creates an Issue and runs Triage end-to-end
- [x] Review UI shows proposal, reasoning, and which Policy rule fired
- [x] Triager can edit urgency, Owner bucket, or Business action before Approval
- [x] Approved path creates a Dry-run record only; no external repo mutation
- [x] One Issue can be demoed from paste through approved dry-run in a single session

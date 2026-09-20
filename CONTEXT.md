# Issue Triage

AI-assisted intake workflow that turns messy GitHub issues into structured, policy-checked actions for a maintainer team — built as an FDE portfolio proof, evaluated on real public Kibana issues.

## Language

**Customer**:
A fictional open-source maintainer team (Kibana-shaped) that the portfolio story treats as the embedded engagement. The real audience is recruiters evaluating FDE skill.
_Avoid_: Client, employer, Kibana Inc as literal customer

**Triager**:
The human who uses the review UI to inspect, edit, approve, or reject a proposed action.
_Avoid_: Support lead, admin, “anyone with the link”

**Issue**:
An incoming request represented by a title and body (from a form or a fetched public GitHub issue). Intake-time input only — not comments, final labels, or later timeline events.
_Avoid_: Ticket (unless speaking loosely), PR

**Triage**:
Producing a structured decision and (when approved) a dry-run operational action. Triage is not fixing the underlying bug.
_Avoid_: Resolution, resolve, close-as-fixed

**Resolution**:
Work a human does after triage (investigate, patch, close). Out of scope for this system.
_Avoid_: Using “resolve” for what the system does

**Intake**:
How an Issue enters the live system: either a paste form (title + body) or import by public GitHub issue number/URL (title + body fetched).
_Avoid_: Webhook (v1), GitHub Issues for this repo’s own work tracking

**Business action**:
One of: `ask_info`, `draft_reply`, `route`, `escalate`. What the system proposes to *do* next.
_Avoid_: Calling “hold for human review” a business action (that is a workflow/approval state)

**Approval**:
A human checkpoint that may be required before a business action is considered approved. Separate from escalate.
_Avoid_: Treating approval as one of the four business actions

**Approval policy**:
Balanced automation: low-risk paths may proceed without waiting on the Triager; high-impact paths always require Approval.
_Avoid_: Auto-approving escalate or p1; requiring Approval on every trivial ask_info

**Dry-run action**:
Recording what the system would do (comment, labels, assignment) in our own database without writing to elastic/kibana or any external repo in v1.
_Avoid_: Mutating Kibana; treating the dry-run log as a second GitHub repo

**Draft reply**:
A response body built from templates filled with structured fields (not a free-form second LLM call) when the business action is `draft_reply` or when `ask_info` needs a comment body.
_Avoid_: Unconstrained LLM prose as the v1 reply mechanism

**Owner**:
A coarse routing bucket (~8–12 groups) the system suggests for who should handle the Issue. Raw Kibana `Team:*` labels are mapped into these buckets for evaluation.
_Avoid_: Using all ~57 raw Team labels as the product’s owner vocabulary in v1

**Policy rule**:
A deterministic check in code that can override the model (for example forcing escalate). Security-related rules match vulnerability language, not the bare word “security.”
_Avoid_: Shipping a default rule that escalates on the substring “security”

**Missed escalation**:
A safety failure where the system should have escalated (or forced Approval on a critical path) and did not. The headline evaluation metric for the portfolio.
_Avoid_: Leading the README with overall accuracy alone

**Eval corpus**:
Filtered historical closed issues from elastic/kibana used to score the system offline. Not the product identity.
_Avoid_: Calling the product a “Kibana classifier”

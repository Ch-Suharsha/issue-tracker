Status: ready-for-agent

# Spec: Issue Triage v1

## Problem Statement

A small open-source maintainer team (Kibana-shaped, fictional Customer used for the portfolio narrative) manually triages a large volume of Issues. Triage is inconsistent across people: urgency is misjudged, ownership is unclear, and high-impact or security-sensitive reports can sit too long because they arrive looking like ordinary bugs. The real audience for this build is recruiters evaluating Forward Deployed Engineer skill — they need evidence of discovery, a reliable operational workflow, deterministic policy where stakes are high, human control, and honest evaluation — not another chatbot demo.

## Solution

Build an AI-assisted Triage system: Intake accepts an Issue (paste form or import by public GitHub issue number/URL). One structured model call proposes category, urgency, Owner bucket, business action, and short reasoning. Deterministic Policy rules may override the model (especially security-sensitive language). A balanced Approval policy lets low-risk paths proceed and always requires a Triager for escalate, p1, and policy overrides. Approved work produces a Dry-run action record only (never writes to elastic/kibana). An offline EvalRunner replays a filtered Eval corpus and reports Missed escalation as the headline metric, with supporting operational metrics. Public DEMO_MODE keeps the live URL safe.

## User Stories

1. As a Triager, I want to paste an Issue title and body into a form, so that I can try Triage without finding a real GitHub URL.
2. As a Triager, I want to import an Issue by public GitHub number or URL, so that I can triage a real Kibana-shaped example using only title and body at Intake.
3. As a Triager, I want Intake to ignore comments, final labels, and later timeline events, so that Triage reflects what was knowable when the Issue arrived.
4. As a Triager, I want the system to propose a category for the Issue, so that I can see how it was classified.
5. As a Triager, I want the system to propose urgency as p1, p2, or p3, so that I can prioritize correctly.
6. As a Triager, I want the system to propose an Owner bucket (not one of ~57 raw team strings), so that routing is understandable in a demo.
7. As a Triager, I want the system to propose one Business action (`ask_info`, `draft_reply`, `route`, or `escalate`), so that the next step is explicit.
8. As a Triager, I want to see short model reasoning, so that I can judge whether the proposal makes sense.
9. As a Triager, I want Policy rules to override unsafe model proposals, so that escalation does not depend on the model having a good day.
10. As a Triager, I want security Policy rules to use vulnerability language, not the bare word “security,” so that product-name noise does not flood escalations.
11. As a Triager, I want empty or unusable Issue bodies to become `ask_info`, so that incomplete reports do not get routed as if they were actionable.
12. As a Triager, I want `escalate` and p1 outcomes to always require Approval, so that high-impact paths stay under human control.
13. As a Triager, I want policy overrides that force escalate to require Approval, so that automatic safety actions are still reviewed.
14. As a Triager, I want low-risk `ask_info` and obvious low-urgency `route` cases to be allowed to proceed without waiting on me in private/dev mode, so that the workflow demonstrates balanced automation.
15. As a Triager, I want Approval to be a checkpoint separate from the `escalate` Business action, so that “needs a human” is not confused with “escalate to a specialist.”
16. As a Triager, I want to pause an Issue awaiting Approval, so that nothing silently continues without me.
17. As a Triager, I want to edit proposed urgency, Owner, or Business action before Approval, so that I can correct the system.
18. As a Triager, I want to approve or reject a proposal, so that I retain final control.
19. As a Triager, I want to resume later from the same workflow state, so that closing my laptop does not lose progress.
20. As a Triager, I want every decision transition written to an audit/decision log, so that I can answer why an Issue was escalated or routed.
21. As a Triager, I want Draft reply / ask-info comment bodies to come from templates filled with structured fields, so that replies are predictable and testable.
22. As a Triager, I want approved actions in v1 to create a Dry-run record (intended comment, labels, assignment), so that the action loop is real without mutating elastic/kibana.
23. As a Triager, I want the system never to write to elastic/kibana, so that the portfolio demo cannot harm an upstream project.
24. As a recruiter using the public demo, I want DEMO_MODE to no-op mutating effects, so that I cannot corrupt demo data or burn unbounded model calls.
25. As a recruiter, I want seeded example Issues visible on first load, so that a cold visit is not an empty app.
26. As a recruiter, I want to see a clear story that this is Triage not Resolution, so that the portfolio does not overclaim.
27. As a maintainer (Customer narrative), I want inconsistent manual Triage reduced, so that high-impact Issues are less likely to sit unnoticed.
28. As a maintainer, I want Owner suggestions in coarse buckets, so that routing discussions stay comprehensible.
29. As a portfolio author, I want an offline EvalRunner over the Eval corpus, so that I can publish honest numbers without clicking the UI for every Issue.
30. As a portfolio author, I want a safety challenge set focused on critical / must-escalate cases, so that Missed escalation is measurable.
31. As a portfolio author, I want an operational eval set with natural class mix and temporal splits by created time, so that overall metrics are not fantasy.
32. As a portfolio author, I want Missed escalation as the README headline metric, so that recruiters see the safety-critical failure mode first.
33. As a portfolio author, I want supporting metrics (routing/urgency agreement, false escalations, human-intervention rate) in a secondary table, so that the story is complete but not vanity-led.
34. As a portfolio author, I want baselines (majority class and a simple classical model) compared to the LLM+policy system, so that model value is proven or honestly limited.
35. As a portfolio author, I want ablations (model-only, rules-only, combined), so that the Policy layer’s contribution is visible.
36. As a portfolio author, I want eval input limited to Intake-safe fields, so that label leakage does not fake performance.
37. As a portfolio author, I want “Failing test” CI Issues excluded from the Eval corpus, so that noise does not dominate scores.
38. As a portfolio author, I want raw corpus cached immutably and live workflow state stored separately, so that reruns are cheap and the app state is clear.
39. As a developer, I want a single structured LLM call per Issue, so that the architecture stays simple and interviewable.
40. As a developer, I want no LangGraph in v1, so that fixed workflow code remains the source of truth for state.
41. As a developer, I want the Classifier behind a port so tests can inject a fake, so that TriagePipeline tests do not need network or API keys.
42. As a developer, I want TriagePipeline as the primary tested behavior seam, so that tests assert external outcomes not private helpers.
43. As a developer, I want transactional writes for proposal, policy result, approval state, and decision log, so that crashes do not leave half-applied Triage.
44. As a developer, I want optimistic concurrency on Approval updates, so that two Triagers cannot silently overwrite each other.
45. As a developer, I want idempotent Intake/import where practical, so that retries do not duplicate work incorrectly.
46. As a developer, I want schema validation failures handled without crashing the workflow into an undefined state, so that bad model output becomes a safe failure/retry/hold path.
47. As a developer, I want discovery brief numbers (~6 maintainers, ~100–150 Issues/week) clearly labeled fictional, so that the README stays honest.
48. As a recruiter, I want a short demo path that includes one Policy override failure case (Issue C style), so that I see engineering judgment not only happy-path UI.
49. As a Triager, I want to see which Policy rule fired (rule id + reason), so that overrides are explainable.
50. As a portfolio author, I want Out of Scope items respected in v1, so that the first ship stays finishable.

## Implementation Decisions

- Single-context product vocabulary is defined in `CONTEXT.md`; ADRs 0001–0004 are binding for v1.
- Primary runtime shape: one web application service (Python, FastAPI) with server-rendered UI (Jinja + HTMX), Postgres for live workflow state (Neon), hosted as a single web service (Render), no task queue and no LangGraph in v1.
- Primary module seam: **TriagePipeline** — accepts an Issue (title, body, optional author metadata), returns the post-policy proposal, approval requirement, workflow status transition, optional Dry-run record, and decision-log entries.
- Classifier port: one structured LLM call producing category, urgency (`p1`|`p2`|`p3`), Owner bucket suggestion, Business action, short reasoning, optional observed signals. Model output is never the authoritative Policy decision.
- Policy module: ordered pure functions; each returns whether it applies, the override fields, `rule_id`, and reason. Security rules match vulnerability language only (not bare “security”).
- Approval policy module: balanced — low-risk `ask_info` and obvious low-urgency `route` may auto-proceed in private/dev; `escalate`, p1, and policy-forced escalate always require Triager Approval. Public DEMO_MODE no-ops mutating effects and avoids unbounded live model spend (prefer seeded/precomputed demos for public).
- Business actions are exactly: `ask_info`, `draft_reply`, `route`, `escalate`. Workflow status (received, classified, awaiting approval, approved, dry-run recorded, failed, etc.) and Approval policy are separate fields from Business action.
- Draft reply / ask-info bodies: templates filled from structured fields; no second free-form LLM writer in v1.
- Dry-run action store: persist intended external effects (comment body, labels, owner assignment) in our database only.
- Intake adapters: (1) form paste; (2) GitHub fetch by issue number/URL limited to title and body (and safe metadata such as author type if needed). No webhooks in v1.
- Owner taxonomy: ~8–12 buckets with a mapping from Kibana `Team:*` labels for evaluation; product UI speaks in buckets.
- Eval corpus: filtered closed elastic/kibana Issues (created since 2023), exclude PRs and titles starting with `Failing test`, dual sets (operational temporal split by `created_at` + safety challenge set). Raw cache on disk; do not commit full Issue bodies to the public repo.
- Secondary seam: **EvalRunner** — batch replay through TriagePipeline (or its batch entrypoint) producing metrics; headline = Missed escalation on the safety set; also false escalations, operational agreement rates, human-intervention rate; baselines and ablations as agreed in research.
- Persistence: workflow row + immutable decision/audit log; optimistic concurrency on Triager updates.
- Observability for v1 can stay minimal (structured logs); full SaaS APM is not required to accept this spec.
- LLM provider choice is re-verified at implement time against current free-tier limits; structured-output validation must fail loudly and safely.

## Testing Decisions

- Good tests assert **external behavior** at seams: given Issue input (and a fake Classifier when needed), assert Business action, urgency after Policy, Approval requirement, Dry-run record shape, and decision-log reasons. Do not assert private helper call sequences or prompt text snapshots unless a prompt regression is the explicit goal.
- **TriagePipeline** is the primary automated test surface (unit/integration with in-memory or test DB as appropriate).
- **EvalRunner** tests focus on metric computation correctness on small fixtures (e.g. known missed-escalation cases), not on live Kibana network calls in CI.
- Classifier is replaced by a fake/adapter in pipeline tests; CI must not require real LLM credentials.
- Prior art: none in-repo yet (greenfield). Establish pytest as the default; keep eval fixtures small and deterministic.
- Add at least one explicit regression for the “model says low urgency / Policy escalates” security-language scenario.
- DEMO_MODE behavior should be tested: mutating paths no-op or refuse safely.

## Out of Scope

- Writing labels, comments, or assignments to elastic/kibana (or any customer production tracker) in v1.
- GitHub webhooks / real-time sync.
- LangGraph or multi-step tool-calling agents.
- Free-form LLM draft replies as the primary reply mechanism.
- Perfect ground-truth claims from raw maintainer labels; labels are noisy reference decisions.
- Full owner fidelity to all ~57 Kibana Team labels.
- Automatic Resolution (code fixes, closing Issues as fixed).
- Multi-Triager enterprise SSO / complex RBAC (beyond basic demo safety).
- Guaranteeing a specific LLM vendor forever (provider is swappable behind the Classifier port).

## Further Notes

- Discovery brief should state fictional Customer scale (~6 maintainers, ~100–150 Issues/week) and the pain (inconsistent Triage, slow high-impact catches), aligned with ADR 0001/0004.
- Portfolio packaging (README six questions, short demo, failure analysis) can follow implementation milestones but is implied by acceptance of Missed escalation as headline.
- Next skill after this spec: `/to-tickets` to split into tracer-bullet tickets under `.scratch/issue-triage-v1/issues/`.

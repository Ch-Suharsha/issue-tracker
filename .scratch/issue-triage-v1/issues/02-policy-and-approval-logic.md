# 02: Policy overrides and Approval requirements

**What to build:** Deterministic Policy rules layered after the Classifier, plus balanced Approval policy logic. The pipeline must override unsafe model proposals (Issue C: security-language body with model saying low urgency still ends escalate + Approval required). Empty or unusable bodies force `ask_info`. Policy records `rule_id` and reason; model reasoning stays separate from authoritative policy decisions.

**Blocked by:** 01: TriagePipeline foundation with fake Classifier

**Status:** done

- [x] Ordered Policy functions can override category, urgency, Business action, and Owner as designed
- [x] Security Policy uses vulnerability language only, not the bare word "security"
- [x] `escalate`, p1, and policy-forced escalate always require Approval
- [x] Low-risk `ask_info` and obvious low-urgency `route` may auto-proceed in private/dev mode
- [x] Regression test: model proposes low urgency on security-language Issue; Policy escalates anyway
- [x] Pipeline tests assert external outcomes at the TriagePipeline seam, not private helpers

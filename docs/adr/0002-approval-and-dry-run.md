# Balanced approval and dry-run actions

Private/dev runs use a balanced Approval policy: low-risk `ask_info` and obvious low-urgency `route` may auto-proceed; `escalate`, p1, and policy overrides always require a Triager. Approved actions in v1 are Dry-run only (log intended comment/labels/assignment); never write to elastic/kibana. `draft_reply` / ask-info comment bodies use templates, not a free-form LLM writer. Public DEMO_MODE still no-ops all mutating effects.

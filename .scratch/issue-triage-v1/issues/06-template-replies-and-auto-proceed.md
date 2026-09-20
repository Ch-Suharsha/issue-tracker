# 06: Template replies and balanced auto-proceed

**What to build:** Template-based bodies for `ask_info` and `draft_reply` (structured fields in, predictable comment out — no second free-form LLM writer). Wire balanced Approval so qualifying low-risk paths auto-proceed in private/dev while escalate and p1 paths still require Triager Approval.

**Blocked by:** 04: Form intake → review → approve → dry-run (first vertical slice)

**Status:** done

- [x] ask_info and draft_reply produce template-filled Dry-run comment bodies
- [x] Auto-proceed applies only to allowed low-risk paths per Approval policy
- [x] Escalate and p1 never auto-proceed without Triager Approval
- [x] Tests cover at least one auto-proceed path and one forced-Approval path

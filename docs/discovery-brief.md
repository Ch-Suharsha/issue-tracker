# Discovery brief — Issue Triage (fictional Customer)

> **Fiction disclaimer:** The Customer, team size, and volume numbers below are a portfolio narrative shaped like a Kibana maintainer team. They are not claims about Elastic or any real employer.

## Customer

A fictional open-source analytics platform (“Kibana-shaped”) maintained by **six core maintainers** across observability, security, and shared UX. The real audience for this build is recruiters evaluating Forward Deployed Engineer skill — discovery, workflow design, policy, and honest eval — not a product pitch to Elastic.

## Scale and pain

| Signal | Estimate (fictional) |
|--------|------------------------|
| Maintainers doing triage | ~6 |
| New GitHub Issues per week | ~100–150 |
| Time on triage per maintainer | ~4–6 hours/week |

**What breaks today**

1. **Inconsistent urgency** — the same report gets p2 from one triager and p3 from another; critical auth issues can look like routine bugs in the title alone.
2. **Unclear ownership** — ~57 raw `Team:*` labels on the upstream repo; routing discussions stall while the issue sits in `needs-triage`.
3. **Slow catches on high-impact reports** — security-sensitive language buried in long bodies; manual review misses session/auth patterns when the queue is deep.
4. **No durable audit trail** — decisions live in Slack threads; hard to answer “why did we escalate this?” six months later.

**What we are not solving in v1:** automatic resolution, mutating the upstream repo, or perfect agreement with noisy maintainer labels.

## Success criteria (portfolio)

- Live **Triage** workflow: intake → structured proposal → deterministic policy → human approval → dry-run action record.
- **Missed escalation** on a safety challenge set is the headline metric (see README).
- Public demo is safe: `DEMO_MODE`, seeded examples, no unbounded LLM spend for anonymous visitors.

## Stakeholders

| Role | Need |
|------|------|
| Triager (maintainer) | Faster consistent proposals; policy catches what the model misses; approval on high-impact paths |
| Security liaison | Mandatory escalation on vulnerability language, not product-name “security” noise |
| Portfolio reviewer | Evidence of discovery, failure analysis, and eval honesty |

See [CONTEXT.md](../CONTEXT.md) for vocabulary and [docs/adr/](../adr/) for binding architecture decisions.

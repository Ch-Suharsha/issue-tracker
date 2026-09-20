# Owner bucket taxonomy

Kibana uses ~57 raw `Team:*` labels. For evaluation and product routing we collapse them into **10 owner buckets** so metrics stay stable and the review UI stays readable.

## Canonical buckets

| Bucket | Scope |
|--------|--------|
| **Security** | Security Solution, threat hunting, detections, entity analytics, cases, response ops |
| **Observability** | Logs/metrics/signals, onboarding, APM/uptime (incl. deprecated teams), Logstash |
| **Dashboards** | Presentation, visualizations, dashboard UX |
| **Fleet** | Fleet/agent control plane, asset management |
| **Search** | Search, Discover, ESQL, Data Discovery, Enterprise Search |
| **Shared UX** | SharedUX, platform design |
| **Platform** | Kibana management, core, migrations, integrations, cloud, operations |
| **ML & AI** | ML, AI infra, agent-builder |
| **Docs** | Documentation team |
| **Other** | Unmapped or missing team labels |

## Mapping rules

1. Strip the `Team:` prefix.
2. Remove trailing `- DEPRECATED` / `DEPRECATED` markers (case-insensitive).
3. Look up the normalized label in `TEAM_TO_BUCKET` (`src/issue_triage/eval/owner_buckets.py`).
4. If an issue has multiple `Team:*` labels, the **first** label in GitHub order is used (same as audit JSONL order).

## Examples

| Raw label | Bucket |
|-----------|--------|
| `Team: SecuritySolution` | Security |
| `Team:Fleet - DEPRECATED` | Fleet |
| `Team:Presentation` | Dashboards |
| `Team:DataDiscovery` | Search |
| `Team:SharedUX` | Shared UX |
| `Team:obs-ux-infra_services - DEPRECATED` | Observability |

## Evaluation notes

- Team labels are **noisy reference routing**, not intake-time facts. The classifier sees only title + body.
- Ground-truth owner for scoring comes from maintainer `Team:*` labels mapped through this table.
- Bucket counts per split are written to `data/eval/split_summary.json` during ingest.

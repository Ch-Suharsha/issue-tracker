from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from issue_triage.eval.corpus import CorpusRecord
from issue_triage.eval.ground_truth import matches_security_language

SplitName = Literal["dev", "test", "safety", "security_escalation", "critical_routing"]


@dataclass
class EvalSplits:
    dev: list[CorpusRecord]
    test: list[CorpusRecord]
    safety: list[CorpusRecord]
    security_escalation: list[CorpusRecord]
    critical_routing: list[CorpusRecord]
    split_cutoff: datetime


def temporal_dev_test_split(
    records: list[CorpusRecord],
    *,
    dev_ratio: float = 0.75,
) -> tuple[list[CorpusRecord], list[CorpusRecord], datetime]:
    if not records:
        now = datetime.now().astimezone()
        return [], [], now

    sorted_records = sorted(records, key=lambda item: (item.created_at, item.number))
    cutoff_index = int(len(sorted_records) * dev_ratio)
    cutoff_index = min(max(cutoff_index, 1), len(sorted_records) - 1)
    cutoff = sorted_records[cutoff_index].created_at
    dev = [record for record in sorted_records if record.created_at < cutoff]
    test = [record for record in sorted_records if record.created_at >= cutoff]
    return dev, test, cutoff


def build_safety_set(records: list[CorpusRecord]) -> list[CorpusRecord]:
    safety: list[CorpusRecord] = []
    seen: set[int] = set()
    for record in records:
        gt = record.ground_truth
        if gt is None:
            continue
        is_critical = gt.impact == "impact:critical"
        has_security = matches_security_language(record.title, record.body)
        if (is_critical or has_security) and record.number not in seen:
            safety.append(record)
            seen.add(record.number)
    safety.sort(key=lambda item: (item.created_at, item.number))
    return safety


def build_security_escalation_set(records: list[CorpusRecord]) -> list[CorpusRecord]:
    selected: list[CorpusRecord] = []
    seen: set[int] = set()
    for record in records:
        gt = record.ground_truth
        if gt is None or not gt.requires_security_escalation:
            continue
        if record.number in seen:
            continue
        selected.append(record)
        seen.add(record.number)
    selected.sort(key=lambda item: (item.created_at, item.number))
    return selected


def build_critical_routing_set(records: list[CorpusRecord]) -> list[CorpusRecord]:
    selected: list[CorpusRecord] = []
    seen: set[int] = set()
    for record in records:
        gt = record.ground_truth
        if gt is None or not gt.requires_critical_routing:
            continue
        if record.number in seen:
            continue
        selected.append(record)
        seen.add(record.number)
    selected.sort(key=lambda item: (item.created_at, item.number))
    return selected


def count_by_impact(records: list[CorpusRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        if record.ground_truth is not None:
            counts[record.ground_truth.impact] += 1
    return dict(counts)


def count_by_owner(records: list[CorpusRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        if record.ground_truth is not None:
            counts[record.ground_truth.owner] += 1
    return dict(counts)


def build_splits(records: list[CorpusRecord], *, dev_ratio: float = 0.75) -> EvalSplits:
    dev, test, cutoff = temporal_dev_test_split(records, dev_ratio=dev_ratio)
    safety = build_safety_set(records)
    security_escalation = build_security_escalation_set(records)
    critical_routing = build_critical_routing_set(records)
    return EvalSplits(
        dev=dev,
        test=test,
        safety=safety,
        security_escalation=security_escalation,
        critical_routing=critical_routing,
        split_cutoff=cutoff,
    )


def split_summary(splits: EvalSplits) -> dict:
    return {
        "split_cutoff_created_at": splits.split_cutoff.isoformat(),
        "counts": {
            "dev": len(splits.dev),
            "test": len(splits.test),
            "safety": len(splits.safety),
            "security_escalation": len(splits.security_escalation),
            "critical_routing": len(splits.critical_routing),
            "total_usable": len(splits.dev) + len(splits.test),
        },
        "impact_by_split": {
            "dev": count_by_impact(splits.dev),
            "test": count_by_impact(splits.test),
            "safety": count_by_impact(splits.safety),
        },
        "owner_by_split": {
            "dev": count_by_owner(splits.dev),
            "test": count_by_owner(splits.test),
            "safety": count_by_owner(splits.safety),
        },
        "safety_breakdown": {
            "critical_only": len(splits.critical_routing),
            "security_language": len(splits.security_escalation),
        },
    }


def write_split_summary(path: Path, splits: EvalSplits) -> dict:
    summary = split_summary(splits)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from issue_triage.eval.ground_truth import GroundTruth, ground_truth_from_record


@dataclass
class CorpusRecord:
    number: int
    title: str
    body: str
    labels: list[str]
    created_at: datetime
    author: str = ""
    author_type: str = "User"
    url: str = ""
    ground_truth: Optional[GroundTruth] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.ground_truth is None:
            self.ground_truth = ground_truth_from_record(
                title=self.title,
                body=self.body,
                labels=self.labels,
            )


def parse_created_at(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def passes_ingest_filters(
    *,
    title: str,
    labels: list[str],
    is_pr: bool = False,
) -> bool:
    if is_pr:
        return False
    if title.startswith("Failing test"):
        return False
    impacts = [
        label
        for label in labels
        if label.startswith("impact:") and label != "impact:needs-assessment"
    ]
    return bool(impacts)


def record_from_audit_row(row: dict, *, body: str = "") -> Optional[CorpusRecord]:
    labels = list(row.get("labels") or [])
    title = row.get("title") or ""
    if not passes_ingest_filters(title=title, labels=labels, is_pr=row.get("is_pr", False)):
        return None

    resolved_body = body
    if not resolved_body:
        resolved_body = row.get("body") or ""

    return CorpusRecord(
        number=int(row["number"]),
        title=title,
        body=resolved_body,
        labels=labels,
        created_at=parse_created_at(row["created_at"]),
        author=row.get("author") or "",
        author_type=row.get("author_type") or "User",
        url=row.get("url") or "",
    )


def load_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_corpus(path: Path) -> list[CorpusRecord]:
    records: list[CorpusRecord] = []
    for row in load_jsonl(path):
        record = record_from_audit_row(row, body=row.get("body") or "")
        if record is not None and record.ground_truth is not None:
            records.append(record)
    records.sort(key=lambda item: (item.created_at, item.number))
    return records


def write_corpus(path: Path, records: list[CorpusRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "number": record.number,
                "title": record.title,
                "body": record.body,
                "labels": record.labels,
                "created_at": record.created_at.isoformat(),
                "author": record.author,
                "author_type": record.author_type,
                "url": record.url,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

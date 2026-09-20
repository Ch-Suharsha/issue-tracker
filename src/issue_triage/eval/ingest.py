from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from issue_triage.eval.corpus import (
    CorpusRecord,
    load_jsonl,
    record_from_audit_row,
    write_corpus,
)
from issue_triage.eval.splits import build_splits, write_split_summary

DEFAULT_AUDIT_PATH = Path("tmp/audit/kibana-impact-audit.jsonl")
DEFAULT_CORPUS_PATH = Path("data/eval/corpus.jsonl")
DEFAULT_SPLIT_SUMMARY_PATH = Path("data/eval/split_summary.json")
GITHUB_API = "https://api.github.com/repos/elastic/kibana/issues"


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "issue-triage-eval/0.1",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_issue_body(number: int, *, retry: int = 3) -> str:
    url = f"{GITHUB_API}/{number}"
    for attempt in range(retry):
        try:
            request = Request(url, headers=_github_headers())
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("body") or ""
        except HTTPError as exc:
            if exc.code == 403 and attempt < retry - 1:
                reset = exc.headers.get("X-RateLimit-Reset")
                sleep_for = 60
                if reset:
                    sleep_for = max(int(reset) - int(time.time()) + 1, 1)
                time.sleep(min(sleep_for, 120))
                continue
            if exc.code == 404:
                return ""
            raise
        except URLError:
            if attempt < retry - 1:
                time.sleep(2**attempt)
                continue
            raise
    return ""


def ingest_from_audit(
    audit_path: Path,
    *,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    split_summary_path: Path = DEFAULT_SPLIT_SUMMARY_PATH,
    fetch_bodies: bool = False,
    limit: Optional[int] = None,
    sleep_seconds: float = 0.0,
) -> dict:
    records: list[CorpusRecord] = []
    missing_bodies = 0

    for index, row in enumerate(load_jsonl(audit_path)):
        if limit is not None and len(records) >= limit:
            break

        body = row.get("body") or ""
        if not body and fetch_bodies:
            body = fetch_issue_body(int(row["number"]))
            if sleep_seconds:
                time.sleep(sleep_seconds)
        if not body:
            missing_bodies += 1

        record = record_from_audit_row(row, body=body)
        if record is not None and record.ground_truth is not None:
            records.append(record)

    write_corpus(corpus_path, records)
    splits = build_splits(records)
    summary = write_split_summary(split_summary_path, splits)

    return {
        "corpus_path": str(corpus_path),
        "split_summary_path": str(split_summary_path),
        "records_written": len(records),
        "missing_bodies": missing_bodies,
        "bodies_fetched": fetch_bodies,
        "split_summary": summary,
    }

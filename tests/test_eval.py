from __future__ import annotations

import json
from pathlib import Path

import pytest

from issue_triage.eval.corpus import load_corpus, passes_ingest_filters, record_from_audit_row
from issue_triage.eval.ground_truth import ground_truth_from_record, matches_security_language
from issue_triage.eval.ingest import ingest_from_audit
from issue_triage.eval.owner_buckets import primary_team_bucket, team_label_to_bucket
from issue_triage.eval.runner import EvalRunner, NeutralClassifier, PipelinePredictor, score_records
from issue_triage.eval.splits import build_splits, build_safety_set
from issue_triage.classifier import FakeClassifier

FIXTURES = Path(__file__).parent / "fixtures" / "eval"
CORPUS_FIXTURE = FIXTURES / "corpus.jsonl"
AUDIT_FIXTURE = FIXTURES / "audit_sample.jsonl"


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(CORPUS_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return corpus


def test_ingest_filters_exclude_failing_test_and_prs():
    assert passes_ingest_filters(title="Failing test: foo", labels=["impact:high"]) is False
    assert passes_ingest_filters(title="Real bug", labels=["impact:high"], is_pr=True) is False
    assert passes_ingest_filters(title="Real bug", labels=["impact:needs-assessment"]) is False
    assert passes_ingest_filters(title="Real bug", labels=["impact:high"]) is True


def test_team_label_mapping():
    assert team_label_to_bucket("Team:Fleet - DEPRECATED") == "Fleet"
    assert team_label_to_bucket("Team:Presentation") == "Dashboards"
    assert team_label_to_bucket("Team:Unknown Widgets") == "Other"
    assert primary_team_bucket(["impact:high", "Team:Search"]) == "Search"


def test_ground_truth_escalation_signals():
    gt = ground_truth_from_record(
        title="Password reset issue",
        body="The password reset link works twice.",
        labels=["bug", "impact:medium", "Team: SecuritySolution"],
    )
    assert gt is not None
    assert gt.should_escalate is True
    assert gt.has_security_language is True
    assert gt.urgency == "p3"

    critical = ground_truth_from_record(
        title="Production outage",
        body="Dashboards fail to load for all users in the cluster.",
        labels=["bug", "impact:critical", "Team:Presentation"],
    )
    assert critical is not None
    assert critical.should_escalate is True
    assert critical.urgency == "p1"


def test_security_language_does_not_match_product_name_only():
    assert matches_security_language("Security Solution UI error", "The security app fails to load.") is False


def test_splits_and_safety_set(fixture_corpus: Path):
    records = load_corpus(fixture_corpus)
    splits = build_splits(records, dev_ratio=0.75)
    assert len(splits.dev) + len(splits.test) == len(records)
    safety = build_safety_set(records)
    assert len(safety) >= 2
    assert any(record.number == 4 for record in safety)
    assert any(record.number == 3 for record in safety)


def test_ingest_from_audit_sample(tmp_path: Path):
    audit_rows = [
        {
            "number": 100,
            "title": "Valid issue",
            "body": "Detailed reproduction with enough characters to pass policy checks easily.",
            "labels": ["bug", "impact:high", "Team:Search"],
            "created_at": "2024-01-01T00:00:00Z",
            "is_pr": False,
        },
        {
            "number": 101,
            "title": "Failing test: ignored",
            "labels": ["impact:high"],
            "created_at": "2024-01-02T00:00:00Z",
            "is_pr": False,
        },
    ]
    audit_path = tmp_path / "audit.jsonl"
    audit_path.write_text("\n".join(json.dumps(row) for row in audit_rows) + "\n", encoding="utf-8")

    summary = ingest_from_audit(
        audit_path,
        corpus_path=tmp_path / "corpus.jsonl",
        split_summary_path=tmp_path / "split_summary.json",
    )
    assert summary["records_written"] == 1
    assert (tmp_path / "split_summary.json").exists()


def test_eval_runner_catches_security_language_cases(fixture_corpus: Path):
    records = load_corpus(fixture_corpus)
    security_records = [
        record
        for record in records
        if record.ground_truth and record.ground_truth.has_security_language
    ]
    assert len(security_records) >= 2

    combined = PipelinePredictor(FakeClassifier(), apply_rules=True)
    rules_only = PipelinePredictor(NeutralClassifier(), apply_rules=True)

    combined_metrics = score_records(
        security_records, combined, mode="combined", split="safety", safety_split=True
    )
    rules_metrics = score_records(
        security_records, rules_only, mode="rules_only", split="safety", safety_split=True
    )
    assert combined_metrics.missed_escalations == 0
    assert rules_metrics.missed_escalations == 0


def test_model_only_can_miss_escalation(fixture_corpus: Path):
    runner = EvalRunner.from_corpus(fixture_corpus)
    results = runner.run(modes=["model_only"])
    model_safety = next(m for m in results["metrics"] if m["mode"] == "model_only" and m["split"] == "safety")
    assert model_safety["missed_escalations"] >= 1


def test_score_records_metrics():
    record = record_from_audit_row(
        {
            "number": 99,
            "title": "Password reset link still works",
            "body": "I used my password reset link twice and it still logged me in.",
            "labels": ["bug", "impact:medium", "Team: SecuritySolution"],
            "created_at": "2024-01-01T00:00:00Z",
            "is_pr": False,
        },
        body="I used my password reset link twice and it still logged me in.",
    )
    assert record is not None
    predictor = PipelinePredictor(FakeClassifier(), apply_rules=True)
    metrics = score_records([record], predictor, mode="combined", split="safety", safety_split=True)
    assert metrics.missed_escalations == 0
    assert metrics.n == 1

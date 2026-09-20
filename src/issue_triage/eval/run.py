from __future__ import annotations

import argparse
import json
from pathlib import Path

from issue_triage.eval.ingest import (
    DEFAULT_AUDIT_PATH,
    DEFAULT_CORPUS_PATH,
    DEFAULT_SPLIT_SUMMARY_PATH,
    ingest_from_audit,
)
from issue_triage.classifier_factory import get_classifier_for_eval
from issue_triage.eval.runner import EvalRunner

DEFAULT_RESULTS_DIR = Path("data/eval/results")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kibana eval ingest and replay harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Build cached eval corpus and splits")
    ingest_parser.add_argument(
        "--audit-path",
        type=Path,
        default=DEFAULT_AUDIT_PATH,
        help="Source audit JSONL (title/metadata; bodies optional)",
    )
    ingest_parser.add_argument(
        "--corpus-path",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help="Output corpus JSONL (gitignored)",
    )
    ingest_parser.add_argument(
        "--split-summary-path",
        type=Path,
        default=DEFAULT_SPLIT_SUMMARY_PATH,
        help="Output split summary JSON",
    )
    ingest_parser.add_argument(
        "--fetch-bodies",
        action="store_true",
        help="Fetch missing bodies from GitHub API (rate-limit aware)",
    )
    ingest_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit records for dev runs",
    )
    ingest_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Sleep between GitHub API calls when fetching bodies",
    )

    run_parser = subparsers.add_parser("run", help="Replay corpus through EvalRunner")
    run_parser.add_argument(
        "--corpus-path",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help="Cached corpus JSONL",
    )
    run_parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory for metrics JSON output",
    )
    run_parser.add_argument(
        "--modes",
        nargs="+",
        default=[
            "combined",
            "model_only",
            "rules_only",
            "baseline_majority",
            "baseline_tfidf",
        ],
        help="Ablation modes to score",
    )
    run_parser.add_argument(
        "--classifier",
        choices=["fake", "jev"],
        default="fake",
        help="Classifier for combined/model_only modes (jev requires TYPESAFE_API_KEY)",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Score only the first N records per eval split (dev runs)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        summary = ingest_from_audit(
            args.audit_path,
            corpus_path=args.corpus_path,
            split_summary_path=args.split_summary_path,
            fetch_bodies=args.fetch_bodies,
            limit=args.limit,
            sleep_seconds=args.sleep_seconds,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "run":
        classifier = get_classifier_for_eval(args.classifier)
        runner = EvalRunner.from_corpus(args.corpus_path, classifier=classifier)
        output_path = runner.run_and_write(
            args.results_dir,
            modes=args.modes,
            limit=args.limit,
        )
        print(json.dumps({"results_path": str(output_path)}, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

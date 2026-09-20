from __future__ import annotations

import os
import sys

from issue_triage.classifier import Classifier, FakeClassifier
from issue_triage.jev_classifier import JevClassifier


def get_classifier(*, demo_mode: bool = False) -> Classifier:
    if demo_mode or os.getenv("CLASSIFIER", "").lower() == "fake":
        return FakeClassifier()
    if os.getenv("TYPESAFE_API_KEY"):
        return JevClassifier()
    return FakeClassifier()


def get_classifier_for_eval(name: str) -> Classifier:
    if name == "jev":
        if not os.getenv("TYPESAFE_API_KEY"):
            print("TYPESAFE_API_KEY is required for --classifier jev", file=sys.stderr)
            raise SystemExit(1)
        return JevClassifier()
    return FakeClassifier()


def get_jev_min_confidence() -> float | None:
    raw = os.getenv("JEV_MIN_CONFIDENCE", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None

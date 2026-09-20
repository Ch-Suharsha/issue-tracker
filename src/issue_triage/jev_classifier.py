from __future__ import annotations

import os

from typesafe_sdk import Choice, ChoiceAnswer, TypeSafeAPIError, TypeSafeClient

from issue_triage.classifier import ClassifierError
from issue_triage.eval.owner_buckets import OWNER_BUCKETS
from issue_triage.models import BusinessAction, ClassificationProposal, IssueInput, Urgency

CATEGORY_CRITERIA = {
    "bug": "Software defect or broken behavior",
    "docs": "Documentation error or missing documentation",
    "feature": "Enhancement or new capability request",
    "question": "Usage question or support inquiry",
    "unknown": "Cannot determine from available text",
}

URGENCY_CRITERIA = {
    "p1": "Critical: security, data loss, or production outage",
    "p2": "Important: significant impact but not an emergency",
    "p3": "Low: cosmetic issue, docs typo, minor inconvenience",
}

ACTION_CRITERIA = {
    "ask_info": "Need more information before acting",
    "draft_reply": "Can respond with clarification or guidance",
    "route": "Route to the appropriate maintainer team",
    "escalate": "Security or high-impact specialist required",
}

OWNER_CRITERIA = {bucket: f"Issues typically owned by the {bucket} team" for bucket in OWNER_BUCKETS}

_VALID_CATEGORIES = set(CATEGORY_CRITERIA)
_VALID_URGENCIES: set[Urgency] = {"p1", "p2", "p3"}
_VALID_ACTIONS: set[BusinessAction] = {"ask_info", "draft_reply", "route", "escalate"}
_VALID_OWNERS = set(OWNER_BUCKETS)


def _build_questions() -> dict[str, Choice]:
    return {
        "category": Choice(
            instructions="What type of GitHub issue is this?",
            criteria=CATEGORY_CRITERIA,
        ),
        "urgency": Choice(
            instructions="What urgency should this issue receive?",
            criteria=URGENCY_CRITERIA,
        ),
        "next_action": Choice(
            instructions="What business action should triage take next?",
            criteria=ACTION_CRITERIA,
        ),
        "owner": Choice(
            instructions="Which maintainer owner bucket should handle this issue?",
            criteria=OWNER_CRITERIA,
        ),
    }


def _format_reasoning(choices: dict[str, ChoiceAnswer]) -> str:
    parts = []
    for key in ("category", "urgency", "next_action", "owner"):
        answer = choices[key]
        parts.append(f"{key}={answer.choice} (conf {answer.confidence:.2f})")
    return "Jev: " + ", ".join(parts)


class JevClassifier:
    """TypeSafe Jev adapter behind the Classifier port."""

    def __init__(
        self,
        client: TypeSafeClient | None = None,
        *,
        model: str | None = None,
    ) -> None:
        self._client = client or TypeSafeClient()
        self._model = model or os.getenv("TYPESAFE_MODEL", "jev-latest")

    def classify(self, issue: IssueInput) -> ClassificationProposal:
        state = f"Title: {issue.title}\n\nBody: {issue.body or '(empty)'}"
        try:
            response = self._client.system_one(
                state=state,
                model=self._model,
                questions=_build_questions(),
            )
        except TypeSafeAPIError as exc:
            raise ClassifierError(f"TypeSafe API error: {exc}") from exc

        required = ("category", "urgency", "next_action", "owner")
        choices = response.choices
        for key in required:
            if key not in choices:
                raise ClassifierError(f"Missing Jev answer for {key!r}")

        category = choices["category"].choice
        urgency = choices["urgency"].choice
        next_action = choices["next_action"].choice
        owner = choices["owner"].choice

        if category not in _VALID_CATEGORIES:
            raise ClassifierError(f"Invalid Jev category {category!r}")
        if urgency not in _VALID_URGENCIES:
            raise ClassifierError(f"Invalid Jev urgency {urgency!r}")
        if next_action not in _VALID_ACTIONS:
            raise ClassifierError(f"Invalid Jev action {next_action!r}")
        if owner not in _VALID_OWNERS:
            owner = "Other"

        min_confidence = min(choices[key].confidence for key in required)

        return ClassificationProposal(
            category=category,
            urgency=urgency,  # type: ignore[arg-type]
            owner=owner,
            next_action=next_action,  # type: ignore[arg-type]
            reasoning=_format_reasoning(choices),
            observed_signals=[f"jev_min_confidence:{min_confidence:.4f}"],
        )

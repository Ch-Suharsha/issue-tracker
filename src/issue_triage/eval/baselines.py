from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from issue_triage.eval.corpus import CorpusRecord
from issue_triage.models import BusinessAction, ClassificationProposal, IssueInput, Urgency

TargetKind = Literal["urgency", "action"]


def issue_text(record: CorpusRecord) -> str:
    return f"{record.title}\n{record.body}".strip()


def labels_for_target(records: list[CorpusRecord], target: TargetKind) -> list[str]:
    labels: list[str] = []
    for record in records:
        gt = record.ground_truth
        if gt is None:
            continue
        if target == "urgency":
            labels.append(gt.urgency)
        else:
            labels.append("escalate" if gt.should_escalate else "route")
    return labels


@dataclass
class MajorityBaseline:
    urgency: Urgency
    action: BusinessAction

    @classmethod
    def fit(cls, train: list[CorpusRecord]) -> "MajorityBaseline":
        urgency_counts = Counter(labels_for_target(train, "urgency"))
        action_counts = Counter(labels_for_target(train, "action"))
        urgency = urgency_counts.most_common(1)[0][0]  # type: ignore[assignment]
        majority_action = action_counts.most_common(1)[0][0]
        action: BusinessAction = "escalate" if majority_action == "escalate" else "route"
        return cls(urgency=urgency, action=action)

    def predict(self, record: CorpusRecord) -> ClassificationProposal:
        return ClassificationProposal(
            category="bug",
            urgency=self.urgency,
            owner="Other",
            next_action=self.action,
            reasoning="Majority-class baseline prediction.",
        )


@dataclass
class TfidfLogRegBaseline:
    urgency_model: Optional[Pipeline] = None
    action_model: Optional[Pipeline] = None

    @classmethod
    def fit(cls, train: list[CorpusRecord]) -> "TfidfLogRegBaseline":
        texts = [issue_text(record) for record in train]
        urgency_labels = labels_for_target(train, "urgency")
        action_labels = labels_for_target(train, "action")

        urgency_model = Pipeline(
            [
                ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ("clf", LogisticRegression(max_iter=1000)),
            ]
        )
        action_model = Pipeline(
            [
                ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ("clf", LogisticRegression(max_iter=1000)),
            ]
        )
        urgency_model.fit(texts, urgency_labels)
        action_model.fit(texts, action_labels)
        return cls(urgency_model=urgency_model, action_model=action_model)

    def predict(self, record: CorpusRecord) -> ClassificationProposal:
        text = issue_text(record)
        assert self.urgency_model is not None and self.action_model is not None
        urgency = self.urgency_model.predict([text])[0]
        action_label = self.action_model.predict([text])[0]
        action: BusinessAction = "escalate" if action_label == "escalate" else "route"
        return ClassificationProposal(
            category="bug",
            urgency=urgency,  # type: ignore[arg-type]
            owner="Other",
            next_action=action,
            reasoning="TF-IDF + LogisticRegression baseline prediction.",
        )

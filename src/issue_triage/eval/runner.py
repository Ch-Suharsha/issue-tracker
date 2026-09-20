from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional, Protocol

from issue_triage.approval import approval_policy_for
from issue_triage.classifier import Classifier, FakeClassifier
from issue_triage.eval.baselines import MajorityBaseline, TfidfLogRegBaseline
from issue_triage.eval.corpus import CorpusRecord, load_corpus
from issue_triage.eval.ground_truth import reference_action_for
from issue_triage.eval.splits import EvalSplits, build_splits
from issue_triage.models import ClassificationProposal, IssueInput, PolicyDecision, TriageOutcome
from issue_triage.policy import apply_policy, merge_proposal

AblationMode = Literal[
    "combined",
    "model_only",
    "rules_only",
    "baseline_majority",
    "baseline_tfidf",
]


class Predictor(Protocol):
    def predict(self, record: CorpusRecord) -> TriageOutcome: ...


class NeutralClassifier:
    """Always proposes routine routing so policy rules drive overrides."""

    def classify(self, issue: IssueInput) -> ClassificationProposal:
        return ClassificationProposal(
            category="bug",
            urgency="p2",
            owner="Other",
            next_action="route",
            reasoning="Neutral stub for rules-only ablation.",
        )


@dataclass
class EvalMetrics:
    mode: AblationMode
    split: str
    n: int
    missed_escalations: int = 0
    missed_escalation_rate: float = 0.0
    false_escalations: int = 0
    false_escalation_rate: float = 0.0
    urgency_agreement: float = 0.0
    action_agreement: float = 0.0
    owner_agreement: float = 0.0
    human_intervention_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "split": self.split,
            "n": self.n,
            "missed_escalations": self.missed_escalations,
            "missed_escalation_rate": round(self.missed_escalation_rate, 4),
            "false_escalations": self.false_escalations,
            "false_escalation_rate": round(self.false_escalation_rate, 4),
            "urgency_agreement": round(self.urgency_agreement, 4),
            "action_agreement": round(self.action_agreement, 4),
            "owner_agreement": round(self.owner_agreement, 4),
            "human_intervention_rate": round(self.human_intervention_rate, 4),
        }


@dataclass
class PipelinePredictor:
    classifier: Classifier
    apply_rules: bool = True

    def predict(self, record: CorpusRecord) -> TriageOutcome:
        issue = IssueInput(
            title=record.title,
            body=record.body,
            author_type=record.author_type,
        )
        proposal = self.classifier.classify(issue)
        if self.apply_rules:
            adjusted, policy = apply_policy(issue, proposal)
            merged = merge_proposal(adjusted, policy)
        else:
            policy = PolicyDecision(applied=False)
            merged = {
                "category": proposal.category,
                "urgency": proposal.urgency,
                "owner": proposal.owner,
                "next_action": proposal.next_action,
                "reasoning": proposal.reasoning,
            }

        requires_approval, approval_kind = approval_policy_for(
            urgency=merged["urgency"],
            next_action=merged["next_action"],
            policy=policy,
            demo_mode=False,
        )
        status = "awaiting_approval" if requires_approval else "classified"
        return TriageOutcome(
            category=merged["category"],
            urgency=merged["urgency"],
            owner=merged["owner"],
            next_action=merged["next_action"],
            reasoning=merged["reasoning"],
            policy=policy,
            requires_approval=requires_approval,
            approval_policy=approval_kind,
            workflow_status=status,
        )


@dataclass
class BaselinePredictor:
    baseline: MajorityBaseline | TfidfLogRegBaseline
    apply_rules: bool = False

    def predict(self, record: CorpusRecord) -> TriageOutcome:
        issue = IssueInput(title=record.title, body=record.body)
        proposal = self.baseline.predict(record)
        if self.apply_rules:
            adjusted, policy = apply_policy(issue, proposal)
            merged = merge_proposal(adjusted, policy)
        else:
            policy = PolicyDecision(applied=False)
            merged = {
                "category": proposal.category,
                "urgency": proposal.urgency,
                "owner": proposal.owner,
                "next_action": proposal.next_action,
                "reasoning": proposal.reasoning,
            }
        requires_approval, approval_kind = approval_policy_for(
            urgency=merged["urgency"],
            next_action=merged["next_action"],
            policy=policy,
            demo_mode=False,
        )
        return TriageOutcome(
            category=merged["category"],
            urgency=merged["urgency"],
            owner=merged["owner"],
            next_action=merged["next_action"],
            reasoning=merged["reasoning"],
            policy=policy,
            requires_approval=requires_approval,
            approval_policy=approval_kind,
            workflow_status="awaiting_approval" if requires_approval else "classified",
        )


def score_records(
    records: list[CorpusRecord],
    predictor: Predictor,
    *,
    mode: AblationMode,
    split: str,
    safety_split: bool,
) -> EvalMetrics:
    missed = 0
    false_esc = 0
    urgency_hits = 0
    action_hits = 0
    owner_hits = 0
    human_interventions = 0
    n = 0

    for record in records:
        gt = record.ground_truth
        if gt is None:
            continue
        outcome = predictor.predict(record)
        n += 1

        if gt.should_escalate and outcome.next_action != "escalate":
            missed += 1
        if not gt.should_escalate and outcome.next_action == "escalate":
            false_esc += 1
        if outcome.urgency == gt.urgency:
            urgency_hits += 1
        if outcome.next_action == reference_action_for(gt):
            action_hits += 1
        if outcome.owner == gt.owner:
            owner_hits += 1
        if outcome.requires_approval:
            human_interventions += 1

    metrics = EvalMetrics(mode=mode, split=split, n=n)
    if n:
        if safety_split:
            should_escalate_n = sum(
                1 for record in records if record.ground_truth and record.ground_truth.should_escalate
            )
            metrics.missed_escalations = missed
            metrics.missed_escalation_rate = missed / should_escalate_n if should_escalate_n else 0.0
        else:
            metrics.false_escalations = false_esc
            metrics.false_escalation_rate = false_esc / n
        metrics.urgency_agreement = urgency_hits / n
        metrics.action_agreement = action_hits / n
        metrics.owner_agreement = owner_hits / n
        metrics.human_intervention_rate = human_interventions / n
    return metrics


@dataclass
class EvalRunner:
    splits: EvalSplits
    classifier: Classifier = field(default_factory=FakeClassifier)

    @classmethod
    def from_corpus(cls, corpus_path: Path, *, classifier: Optional[Classifier] = None) -> "EvalRunner":
        records = load_corpus(corpus_path)
        return cls(splits=build_splits(records), classifier=classifier or FakeClassifier())

    def _predictor_for(self, mode: AblationMode) -> tuple[Predictor, MajorityBaseline | TfidfLogRegBaseline | None]:
        if mode == "combined":
            return PipelinePredictor(self.classifier, apply_rules=True), None
        if mode == "model_only":
            return PipelinePredictor(self.classifier, apply_rules=False), None
        if mode == "rules_only":
            return PipelinePredictor(NeutralClassifier(), apply_rules=True), None
        if mode == "baseline_majority":
            baseline = MajorityBaseline.fit(self.splits.dev)
            return BaselinePredictor(baseline), baseline
        if mode == "baseline_tfidf":
            baseline = TfidfLogRegBaseline.fit(self.splits.dev)
            return BaselinePredictor(baseline), baseline
        raise ValueError(f"Unknown ablation mode: {mode}")

    def run(
        self,
        modes: Optional[list[AblationMode]] = None,
        *,
        limit: int | None = None,
    ) -> dict:
        modes = modes or [
            "combined",
            "model_only",
            "rules_only",
            "baseline_majority",
            "baseline_tfidf",
        ]
        safety_records = self.splits.safety[:limit] if limit else self.splits.safety
        test_records = self.splits.test[:limit] if limit else self.splits.test
        results: dict = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "split_counts": {
                "dev": len(self.splits.dev),
                "test": len(test_records),
                "safety": len(safety_records),
            },
            "metrics": [],
        }
        if limit:
            results["limit"] = limit

        for mode in modes:
            predictor, _ = self._predictor_for(mode)
            safety_metrics = score_records(
                safety_records,
                predictor,
                mode=mode,
                split="safety",
                safety_split=True,
            )
            test_metrics = score_records(
                test_records,
                predictor,
                mode=mode,
                split="test",
                safety_split=False,
            )
            results["metrics"].extend([safety_metrics.to_dict(), test_metrics.to_dict()])

        return results

    def run_and_write(
        self,
        output_dir: Path,
        modes: Optional[list[AblationMode]] = None,
        *,
        limit: int | None = None,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = self.run(modes=modes, limit=limit)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = output_dir / f"eval_{timestamp}.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        latest_path = output_dir / "latest.json"
        latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional, Protocol

SplitKind = Literal["security_escalation", "critical_routing", "test", "legacy_safety"]

from issue_triage.approval import approval_policy_for
from issue_triage.classifier import Classifier, FakeClassifier
from issue_triage.eval.baselines import MajorityBaseline, TfidfLogRegBaseline
from issue_triage.eval.corpus import CorpusRecord, load_corpus
from issue_triage.eval.ground_truth import reference_action_for
from issue_triage.eval.splits import EvalSplits, build_splits
from issue_triage.models import ClassificationProposal, IssueInput, PolicyDecision, TriageOutcome
from issue_triage.classifier import parse_jev_min_confidence
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
        outcome, _ = self.predict_with_trace(record)
        return outcome

    def _build_outcome(
        self,
        record: CorpusRecord,
        proposal: ClassificationProposal,
        *,
        policy: PolicyDecision,
        merged: dict,
    ) -> TriageOutcome:
        requires_approval, approval_kind = approval_policy_for(
            urgency=merged["urgency"],
            next_action=merged["next_action"],
            policy=policy,
            demo_mode=False,
            model_min_confidence=parse_jev_min_confidence(proposal.observed_signals),
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

    def predict_with_trace(self, record: CorpusRecord) -> tuple[TriageOutcome, dict]:
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

        outcome = self._build_outcome(record, proposal, policy=policy, merged=merged)
        gt = record.ground_truth
        reference_action = reference_action_for(gt) if gt else None
        outcome_action = merged["next_action"]
        trace = {
            "number": record.number,
            "title": record.title,
            "body_len": len(record.body.strip()),
            "mode": None,
            "split": None,
            "proposal": {
                "category": proposal.category,
                "urgency": proposal.urgency,
                "owner": proposal.owner,
                "next_action": proposal.next_action,
                "reasoning": proposal.reasoning,
            },
            "policy_applied": policy.applied,
            "policy_rule_id": policy.rule_id,
            "merged": {
                "category": merged["category"],
                "urgency": merged["urgency"],
                "owner": merged["owner"],
                "next_action": merged["next_action"],
            },
            "requires_approval": outcome.requires_approval,
            "approval_policy": outcome.approval_policy,
            "ground_truth": {
                "impact": gt.impact if gt else None,
                "urgency": gt.urgency if gt else None,
                "owner": gt.owner if gt else None,
                "should_escalate": gt.should_escalate if gt else None,
                "has_security_language": gt.has_security_language if gt else None,
                "reference_action": reference_action,
            },
            "missed_escalation": bool(
                gt and gt.should_escalate and outcome_action != "escalate"
            ),
            "false_escalation": bool(
                gt and not gt.should_escalate and outcome_action == "escalate"
            ),
            "action_match": outcome_action == reference_action if reference_action else None,
        }
        return outcome, trace

    def predict_trace(self, record: CorpusRecord) -> dict:
        _, trace = self.predict_with_trace(record)
        return trace


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
    split_kind: Literal["security_escalation", "critical_routing", "test", "legacy_safety"],
    traces: list[dict] | None = None,
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
        if traces is not None and isinstance(predictor, PipelinePredictor):
            outcome, trace = predictor.predict_with_trace(record)
            trace["mode"] = mode
            trace["split"] = split
            traces.append(trace)
        else:
            outcome = predictor.predict(record)
        n += 1

        if split_kind in {"security_escalation", "legacy_safety"}:
            if gt.requires_security_escalation and outcome.next_action != "escalate":
                missed += 1
        elif split_kind == "test":
            if not gt.requires_security_escalation and outcome.next_action == "escalate":
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
        if split_kind == "security_escalation":
            should_escalate_n = sum(
                1
                for record in records
                if record.ground_truth and record.ground_truth.requires_security_escalation
            )
            metrics.missed_escalations = missed
            metrics.missed_escalation_rate = missed / should_escalate_n if should_escalate_n else 0.0
        elif split_kind == "legacy_safety":
            should_escalate_n = sum(
                1 for record in records if record.ground_truth and record.ground_truth.should_escalate
            )
            metrics.missed_escalations = missed
            metrics.missed_escalation_rate = missed / should_escalate_n if should_escalate_n else 0.0
        elif split_kind == "test":
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
        collect_traces: bool = False,
    ) -> dict:
        modes = modes or [
            "combined",
            "model_only",
            "rules_only",
            "baseline_majority",
            "baseline_tfidf",
        ]
        security_records = (
            self.splits.security_escalation[:limit]
            if limit
            else self.splits.security_escalation
        )
        critical_records = (
            self.splits.critical_routing[:limit] if limit else self.splits.critical_routing
        )
        test_records = self.splits.test[:limit] if limit else self.splits.test
        results: dict = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "split_counts": {
                "dev": len(self.splits.dev),
                "test": len(test_records),
                "safety": len(self.splits.safety),
                "security_escalation": len(security_records),
                "critical_routing": len(critical_records),
            },
            "metrics": [],
        }
        if limit:
            results["limit"] = limit

        traces: list[dict] = []
        trace_modes = {"combined"} if collect_traces else set()

        for mode in modes:
            predictor, _ = self._predictor_for(mode)
            mode_traces = traces if mode in trace_modes else None
            security_metrics = score_records(
                security_records,
                predictor,
                mode=mode,
                split="security_escalation",
                split_kind="security_escalation",
                traces=mode_traces,
            )
            critical_metrics = score_records(
                critical_records,
                predictor,
                mode=mode,
                split="critical_routing",
                split_kind="critical_routing",
                traces=mode_traces,
            )
            test_metrics = score_records(
                test_records,
                predictor,
                mode=mode,
                split="test",
                split_kind="test",
                traces=mode_traces,
            )
            results["metrics"].extend(
                [
                    security_metrics.to_dict(),
                    critical_metrics.to_dict(),
                    test_metrics.to_dict(),
                ]
            )

        if collect_traces:
            results["trace_count"] = len(traces)
            results["_traces"] = traces

        return results

    def run_and_write(
        self,
        output_dir: Path,
        modes: Optional[list[AblationMode]] = None,
        *,
        limit: int | None = None,
        collect_traces: bool = True,
        results_name: str | None = None,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = self.run(modes=modes, limit=limit, collect_traces=collect_traces)
        traces = payload.pop("_traces", [])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stem = results_name or f"eval_{timestamp}"
        output_path = output_dir / f"{stem}.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if collect_traces and traces:
            trace_path = output_dir / f"trace_{stem}.jsonl"
            trace_path.write_text(
                "\n".join(json.dumps(row) for row in traces) + "\n",
                encoding="utf-8",
            )
        latest_path = output_dir / "latest.json"
        latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

from __future__ import annotations

from dataclasses import dataclass

from issue_triage.eval.corpus import CorpusRecord
from issue_triage.policy import MIN_BODY_CHARS


@dataclass(frozen=True)
class CorpusBodyStats:
    total: int
    empty: int
    short: int
    adequate: int

    @property
    def non_empty_rate(self) -> float:
        return (self.total - self.empty) / self.total if self.total else 0.0

    @property
    def adequate_rate(self) -> float:
        return self.adequate / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "empty": self.empty,
            "short": self.short,
            "adequate": self.adequate,
            "non_empty_rate": round(self.non_empty_rate, 4),
            "adequate_rate": round(self.adequate_rate, 4),
        }


def corpus_body_stats(records: list[CorpusRecord]) -> CorpusBodyStats:
    empty = short = adequate = 0
    for record in records:
        length = len(record.body.strip())
        if length == 0:
            empty += 1
        elif length < MIN_BODY_CHARS:
            short += 1
        else:
            adequate += 1
    return CorpusBodyStats(
        total=len(records),
        empty=empty,
        short=short,
        adequate=adequate,
    )


def assert_corpus_body_quality(
    records: list[CorpusRecord],
    *,
    min_non_empty_rate: float = 0.95,
    label: str = "corpus",
) -> CorpusBodyStats:
    stats = corpus_body_stats(records)
    if stats.non_empty_rate < min_non_empty_rate:
        raise AssertionError(
            f"{label}: non-empty body rate {stats.non_empty_rate:.1%} "
            f"below minimum {min_non_empty_rate:.1%} "
            f"({stats.empty}/{stats.total} empty)"
        )
    return stats

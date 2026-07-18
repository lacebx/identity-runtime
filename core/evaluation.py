from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import uuid
from datetime import datetime


class EvalDimension(Enum):
    """What aspect of identity behavior is being evaluated."""
    CONSISTENCY = "consistency"   # Does output match stated identity?
    ALIGNMENT = "alignment"       # Does output align with goals?
    QUALITY = "quality"           # Raw output quality
    POLICY = "policy"             # Policy compliance
    GROWTH = "growth"             # Is the identity improving over time?
    EMPATHY = "empathy"           # Relational/social dimension


class EvalOutcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class EvalCriterion:
    """
    A single evaluator function bound to a dimension.
    The scorer returns a float in [0.0, 1.0].
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    dimension: EvalDimension = EvalDimension.QUALITY
    description: str = ""
    scorer: Optional[Callable[[Any, Any], float]] = field(default=None, repr=False)
    weight: float = 1.0    # Relative importance
    threshold: float = 0.5  # Minimum passing score
    enabled: bool = True

    def score(self, input_data: Any, output_data: Any) -> float:
        """Run the scorer and return a 0.0–1.0 score."""
        if not self.enabled or not self.scorer:
            return 1.0
        try:
            return float(self.scorer(input_data, output_data))
        except Exception:
            return 0.0


@dataclass
class EvalRecord:
    """A single evaluation result for one interaction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    identity_id: str = ""
    interaction_id: str = ""
    dimension: EvalDimension = EvalDimension.QUALITY
    criterion_name: str = ""
    score: float = 0.0
    outcome: EvalOutcome = EvalOutcome.SKIP
    notes: str = ""
    input_snapshot: Any = None
    output_snapshot: Any = None
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    """Aggregated evaluation report for an interaction or session."""
    identity_id: str
    interaction_id: str
    records: List[EvalRecord] = field(default_factory=list)
    overall_score: float = 0.0
    passed: bool = True
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def summarize(self) -> str:
        lines = [
            f"Evaluation Report — Identity: {self.identity_id}",
            f"Interaction: {self.interaction_id}",
            f"Overall Score: {self.overall_score:.2f} | {'PASS' if self.passed else 'FAIL'}",
            "Criteria:"
        ]
        for r in self.records:
            lines.append(
                f"  [{r.outcome.value.upper()}] {r.criterion_name} "
                f"({r.dimension.value}): {r.score:.2f}"
            )
        return "\n".join(lines)


class EvaluationEngine:
    """
    The Evaluation Engine is a core IdentityOS asset.
    It runs criteria against identity behavior to measure:
    - How well the identity stays true to itself (consistency)
    - How well responses align with goals
    - Whether policies are being respected
    - Growth trajectory over time

    Results feed back into Identity Evolution (versioning/branching).
    """

    def __init__(self):
        self._criteria: Dict[str, EvalCriterion] = {}
        self._history: List[EvalReport] = []

    def add_criterion(self, criterion: EvalCriterion) -> None:
        self._criteria[criterion.id] = criterion

    def remove_criterion(self, criterion_id: str) -> bool:
        return bool(self._criteria.pop(criterion_id, None))

    def evaluate(
        self,
        identity_id: str,
        interaction_id: str,
        input_data: Any,
        output_data: Any,
        dimensions: Optional[List[EvalDimension]] = None
    ) -> EvalReport:
        """
        Evaluate an interaction across all (or specified) dimensions.
        Returns an EvalReport with per-criterion scores and an overall score.
        """
        applicable = [
            c for c in self._criteria.values()
            if c.enabled and (dimensions is None or c.dimension in dimensions)
        ]

        records: List[EvalRecord] = []
        total_weight = 0.0
        weighted_score = 0.0

        for criterion in applicable:
            raw_score = criterion.score(input_data, output_data)
            outcome = (
                EvalOutcome.PASS if raw_score >= criterion.threshold
                else EvalOutcome.FAIL
            )
            record = EvalRecord(
                identity_id=identity_id,
                interaction_id=interaction_id,
                dimension=criterion.dimension,
                criterion_name=criterion.name,
                score=raw_score,
                outcome=outcome,
                input_snapshot=input_data,
                output_snapshot=output_data
            )
            records.append(record)
            weighted_score += raw_score * criterion.weight
            total_weight += criterion.weight

        overall = weighted_score / total_weight if total_weight > 0 else 1.0
        passed = all(r.outcome != EvalOutcome.FAIL for r in records)

        report = EvalReport(
            identity_id=identity_id,
            interaction_id=interaction_id,
            records=records,
            overall_score=overall,
            passed=passed
        )
        self._history.append(report)
        return report

    def history(self, identity_id: Optional[str] = None) -> List[EvalReport]:
        if identity_id:
            return [r for r in self._history if r.identity_id == identity_id]
        return list(self._history)

    def growth_trend(
        self, identity_id: str, last_n: int = 10
    ) -> List[float]:
        """Return overall scores from most recent N evaluations for trend analysis."""
        reports = self.history(identity_id)[-last_n:]
        return [r.overall_score for r in reports]

    def __len__(self) -> int:
        return len(self._criteria)

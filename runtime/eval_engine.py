"""
DEPRECATED — runtime/eval_engine.py

This module has been superseded by core/evaluation.py.

The heuristic classification and scoring functions now live in core/evaluation
as public API functions (classify_memory_type, compute_relevance,
is_worth_remembering, heuristic_memory_scorer, register_default_criteria).

The canonical EvaluationEngine class also lives at core/evaluation.

This shim remains for backward compatibility during the transition.
New code should import directly from core.evaluation.
"""

from core.evaluation import (
    EvaluationEngine,
    EvalCriterion,
    EvalRecord,
    EvalReport,
    EvalOutcome,
    EvalDimension,
    classify_memory_type,
    compute_relevance,
    is_worth_remembering,
    heuristic_memory_scorer,
    register_default_criteria,
)

EvalEngine = EvaluationEngine

__all__ = [
    "EvaluationEngine",
    "EvalEngine",
    "EvalCriterion",
    "EvalRecord",
    "EvalReport",
    "EvalOutcome",
    "EvalDimension",
    "classify_memory_type",
    "compute_relevance",
    "is_worth_remembering",
    "heuristic_memory_scorer",
    "register_default_criteria",
]

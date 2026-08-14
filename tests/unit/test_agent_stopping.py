"""Unit tests for Phase 7 StoppingConditionEvaluator."""

from codegraph.agent.models import (
    InvestigationHypothesis,
    InvestigationQuestion,
    InvestigationState,
)
from codegraph.agent.stopping import StoppingConditionEvaluator


def test_stopping_on_strong_evidence() -> None:
    evaluator = StoppingConditionEvaluator()
    q = InvestigationQuestion(text="Q", repository_id="repo")
    hyp = InvestigationHypothesis(id="H1", statement="S", status="SUPPORTED", confidence="HIGH")
    state = InvestigationState(question=q, hypotheses=(hyp,))

    stop, reason = evaluator.should_stop(state)
    assert stop is True
    assert "Strong evidence" in reason


def test_stopping_on_max_iterations() -> None:
    evaluator = StoppingConditionEvaluator(custom_budget={"max_iterations": 2})
    q = InvestigationQuestion(text="Q", repository_id="repo")
    state = InvestigationState(question=q, iteration=2)

    stop, reason = evaluator.should_stop(state)
    assert stop is True
    assert "max_iterations" in reason

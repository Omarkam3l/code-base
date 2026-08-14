"""Unit tests for Phase 7 EvidenceEvaluator and hypothesis updates."""

from codegraph.agent.evaluator import EvidenceEvaluator
from codegraph.agent.models import (
    InvestigationHypothesis,
    InvestigationQuestion,
    InvestigationState,
)
from codegraph.rag.models import Evidence


def test_evidence_evaluator_support() -> None:
    evaluator = EvidenceEvaluator()
    q = InvestigationQuestion(text="Why does UserService fail?", repository_id="repo")
    hyp = InvestigationHypothesis(id="H1", statement="UserService lookup fails")
    ev1 = Evidence(
        citation_id="E1",
        entity_id="func:UserService",
        entity_type="function",
        qualified_name="UserService",
        file_path="services.py",
        start_line=1,
        end_line=10,
        source_code="def UserService(): pass",
        retrieval_score=1.0,
    )
    ev2 = Evidence(
        citation_id="E2",
        entity_id="func:get_user",
        entity_type="function",
        qualified_name="get_user",
        file_path="services.py",
        start_line=11,
        end_line=20,
        source_code="def get_user(): pass",
        retrieval_score=1.0,
    )

    state = InvestigationState(question=q, hypotheses=(hyp,), evidence=(ev1, ev2))
    new_state = evaluator.evaluate_state(state)

    assert new_state.hypotheses[0].status == "SUPPORTED"
    assert new_state.hypotheses[0].confidence in ("HIGH", "MEDIUM")

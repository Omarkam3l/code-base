"""Unit tests for Phase 7 Deterministic and LLM planners."""

from codegraph.agent.models import InvestigationQuestion
from codegraph.agent.planner import DeterministicPlanner, LLMInvestigationPlanner
from codegraph.rag.llm import FakeLLMProvider


def test_deterministic_planner_init() -> None:
    planner = DeterministicPlanner()
    q = InvestigationQuestion(text="Why does authentication fail?", repository_id="repo")
    state = planner.initialize_state(q)
    assert len(state.hypotheses) > 0
    assert state.hypotheses[0].confidence == "MEDIUM"


def test_deterministic_planner_steps() -> None:
    planner = DeterministicPlanner()
    q = InvestigationQuestion(text="Why does UserService fail?", repository_id="repo")
    state = planner.initialize_state(q)

    step1 = planner.get_next_step(state)
    assert step1 is not None
    assert step1.operation == "hybrid_search"


def test_llm_planner_json_fallback() -> None:
    fake_llm = FakeLLMProvider()
    planner = LLMInvestigationPlanner(llm_provider=fake_llm)
    q = InvestigationQuestion(text="Investigate issue", repository_id="repo")
    state = planner.initialize_state(q)

    step = planner.get_next_step(state)
    assert step is not None

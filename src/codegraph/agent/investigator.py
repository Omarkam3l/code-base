"""Codebase Investigator orchestrating bounded investigation loop, evidence extraction, and tracing."""

import time
from typing import Any, Mapping
from codegraph.agent.answer import AgentAnswerGenerator
from codegraph.agent.evaluator import EvidenceEvaluator
from codegraph.agent.evidence import AgentEvidenceManager
from codegraph.agent.models import (
    InvestigationAnswer,
    InvestigationQuestion,
    InvestigationState,
)
from codegraph.agent.planner import BaseInvestigationPlanner, DeterministicPlanner
from codegraph.agent.state import StateManager
from codegraph.agent.stopping import StoppingConditionEvaluator
from codegraph.agent.tool_registry import ToolRegistry


class CodebaseInvestigator:
    """Orchestrates autonomous, read-only codebase investigations with bounded iteration loops."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        planner: BaseInvestigationPlanner | None = None,
        state_manager: StateManager | None = None,
        evidence_manager: AgentEvidenceManager | None = None,
        evaluator: EvidenceEvaluator | None = None,
        stopping_evaluator: StoppingConditionEvaluator | None = None,
        answer_generator: AgentAnswerGenerator | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.planner = planner or DeterministicPlanner()
        self.state_manager = state_manager or StateManager()
        self.evidence_manager = evidence_manager or AgentEvidenceManager()
        self.evaluator = evaluator or EvidenceEvaluator()
        self.stopping_evaluator = stopping_evaluator or StoppingConditionEvaluator()
        self.answer_generator = answer_generator or AgentAnswerGenerator()

    def investigate(
        self,
        question: str | InvestigationQuestion,
        repository_id: str = "repo",
        source_code_map: Mapping[str, str] | None = None,
    ) -> InvestigationAnswer:
        """Execute autonomous, bounded investigation loop for a question."""
        t_start = time.perf_counter()

        if isinstance(question, str):
            q_obj = InvestigationQuestion(text=question, repository_id=repository_id)
        else:
            q_obj = question

        state = self.planner.initialize_state(q_obj)
        trace_steps: list[dict[str, Any]] = []

        while True:
            elapsed = time.perf_counter() - t_start
            should_stop, reason = self.stopping_evaluator.should_stop(state, elapsed_sec=elapsed)
            if should_stop:
                break

            step = self.planner.get_next_step(state)
            if not step:
                break

            result = self.tool_registry.execute_step(step, q_obj.repository_id)
            new_ev = self.evidence_manager.extract_evidence_from_result(result, source_code_map=source_code_map)

            state = self.state_manager.update_state(state, step, result, new_ev)
            state = self.evaluator.evaluate_state(state, result)

            trace_steps.append(
                {
                    "step_id": step.id,
                    "operation": step.operation,
                    "arguments": step.arguments,
                    "reason": step.reason,
                    "execution_time_ms": result.execution_time,
                    "evidence_count": len(new_ev),
                    "success": result.success,
                }
            )

        ev_graph = self.evidence_manager.build_evidence_graph(state.evidence)
        t_end = time.perf_counter()
        exec_ms = (t_end - t_start) * 1000.0

        ans = self.answer_generator.generate_answer(state, ev_graph, execution_time_ms=exec_ms)

        # Attach investigation trace to answer
        return InvestigationAnswer(
            answer=ans.answer,
            hypotheses=ans.hypotheses,
            evidence_ids=ans.evidence_ids,
            citations=ans.citations,
            confidence=ans.confidence,
            insufficient_evidence=ans.insufficient_evidence,
            trace=tuple(trace_steps),
            conflicting_evidence=ans.conflicting_evidence,
            execution_time_ms=exec_ms,
        )

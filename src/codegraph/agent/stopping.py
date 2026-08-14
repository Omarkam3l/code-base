"""Stopping condition evaluator enforcing budgets, evidence sufficiency, and terminal criteria."""

from typing import Any
from codegraph.agent.models import InvestigationState


class StoppingConditionEvaluator:
    """Evaluates terminal criteria and budget exhaustion rules to safely halt investigation loops."""

    DEFAULT_BUDGET = {
        "max_steps": 12,
        "max_iterations": 10,
        "max_tool_calls": 30,
        "max_evidence_items": 100,
        "max_context_characters": 50000,
        "max_elapsed_sec": 30.0,
    }

    def __init__(self, custom_budget: dict[str, Any] | None = None) -> None:
        self.budget = dict(self.DEFAULT_BUDGET)
        if custom_budget:
            self.budget.update(custom_budget)

    def should_stop(self, state: InvestigationState, elapsed_sec: float = 0.0) -> tuple[bool, str]:
        """Evaluate if investigation should stop.

        Returns:
            Tuple of (should_stop: bool, reason: str).
        """

        # 1. Strong Evidence Support
        for hyp in state.hypotheses:
            if hyp.status == "SUPPORTED" and hyp.confidence == "HIGH":
                return True, f"Strong evidence found supporting hypothesis {hyp.id}."

        # 2. All Hypotheses Investigated & Resolved
        if state.hypotheses and all(h.status in ("SUPPORTED", "REJECTED", "CONTRADICTED") for h in state.hypotheses):
            return True, "All hypotheses investigated and resolved."

        # 3. Budget Exhaustion Checks
        if state.iteration >= self.budget["max_iterations"]:
            return True, f"Budget exhausted: reached max_iterations ({self.budget['max_iterations']})."

        if len(state.completed_steps) >= self.budget["max_steps"]:
            return True, f"Budget exhausted: reached max_steps ({self.budget['max_steps']})."

        if len(state.evidence) >= self.budget["max_evidence_items"]:
            return True, f"Budget exhausted: reached max_evidence_items ({self.budget['max_evidence_items']})."

        if elapsed_sec >= self.budget["max_elapsed_sec"]:
            return True, f"Budget exhausted: reached max_elapsed_sec ({self.budget['max_elapsed_sec']}s)."

        # 4. No Additional Useful Evidence (3 consecutive empty results)
        if len(state.results) >= 3:
            recent_results = state.results[-3:]
            if all(r.result is None or r.result == [] or r.result == {} for r in recent_results):
                return True, "No additional useful evidence found in 3 consecutive steps."

        return False, "Continue investigation"

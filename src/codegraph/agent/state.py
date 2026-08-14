"""State manager for immutable state transitions and budget tracking."""

from typing import Sequence
from codegraph.agent.models import (
    InvestigationResult,
    InvestigationState,
    InvestigationStep,
)
from codegraph.rag.models import Evidence


class StateManager:
    """Manages immutable updates to InvestigationState."""

    def update_state(
        self,
        state: InvestigationState,
        step: InvestigationStep,
        result: InvestigationResult,
        new_evidence: Sequence[Evidence] = (),
    ) -> InvestigationState:
        """Return a new updated immutable InvestigationState instance."""
        updated_steps = list(state.completed_steps) + [step]
        updated_results = list(state.results) + [result]

        # Deduplicate evidence
        seen_ids = {ev.entity_id for ev in state.evidence}
        merged_evidence = list(state.evidence)
        for ev in new_evidence:
            if ev.entity_id not in seen_ids:
                merged_evidence.append(ev)
                seen_ids.add(ev.entity_id)

        budget = dict(state.budget_remaining)
        if "max_steps" in budget:
            budget["max_steps"] -= 1

        return InvestigationState(
            question=state.question,
            hypotheses=state.hypotheses,
            completed_steps=tuple(updated_steps),
            results=tuple(updated_results),
            evidence=tuple(merged_evidence),
            open_questions=state.open_questions,
            iteration=state.iteration + 1,
            budget_remaining=budget,
            status=state.status,
            conflicting_evidence=state.conflicting_evidence,
        )

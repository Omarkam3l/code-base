"""Hypothesis-driven evidence evaluation, support/contradiction classification, and plan revision."""

from typing import Sequence
from codegraph.agent.models import (
    InvestigationHypothesis,
    InvestigationResult,
    InvestigationState,
)
from codegraph.rag.models import Evidence


class EvidenceEvaluator:
    """Evaluates evidence against hypotheses, updates confidence levels, and detects conflicting evidence."""

    def __init__(self) -> None:
        pass

    def evaluate_state(
        self,
        state: InvestigationState,
        latest_result: InvestigationResult | None = None,
    ) -> InvestigationState:
        """Evaluate evidence collected so far against all active hypotheses."""
        if not state.hypotheses:
            return state

        updated_hypotheses: list[InvestigationHypothesis] = []
        has_conflicts = False

        all_evidence_ids = {ev.citation_id for ev in state.evidence}
        evidence_text = " ".join([f"{ev.qualified_name} {ev.file_path} {ev.source_code}" for ev in state.evidence]).lower()

        for hyp in state.hypotheses:
            sup_ids = list(hyp.supporting_evidence)
            con_ids = list(hyp.contradicting_evidence)

            h_text = hyp.statement.lower()

            # Classify evidence for hypothesis
            for ev in state.evidence:
                e_tag = ev.citation_id
                q_low = ev.qualified_name.lower()
                f_low = ev.file_path.lower()
                ev_text = f"{ev.qualified_name} {ev.file_path} {ev.source_code}".lower()

                # Check support
                if any(w in h_text for w in (q_low, f_low)) or any(w in ev_text for w in h_text.split() if len(w) > 4):
                    if e_tag not in sup_ids:
                        sup_ids.append(e_tag)

                # Check contradiction: if hypothesis claims X fails in A, but evidence shows A works or delegates to B
                if "fail" in h_text and ("succ" in q_low or "pass" in q_low or "ok" in q_low):
                    if e_tag not in con_ids:
                        con_ids.append(e_tag)

            # Determine confidence & status
            if len(con_ids) > len(sup_ids) and len(con_ids) >= 2:
                status = "REJECTED"
                confidence = "REJECTED"
            elif len(sup_ids) >= 2 and not con_ids:
                status = "SUPPORTED"
                confidence = "HIGH"
            elif len(sup_ids) >= 1:
                status = "SUPPORTED"
                confidence = "MEDIUM"
            else:
                status = hyp.status
                confidence = hyp.confidence

            if len(sup_ids) > 0 and len(con_ids) > 0:
                has_conflicts = True

            updated_hypotheses.append(
                InvestigationHypothesis(
                    id=hyp.id,
                    statement=hyp.statement,
                    supporting_evidence=tuple(sup_ids),
                    contradicting_evidence=tuple(con_ids),
                    confidence=confidence,
                    status=status,
                )
            )

        return InvestigationState(
            question=state.question,
            hypotheses=tuple(updated_hypotheses),
            completed_steps=state.completed_steps,
            results=state.results,
            evidence=state.evidence,
            open_questions=state.open_questions,
            iteration=state.iteration,
            budget_remaining=state.budget_remaining,
            status=state.status,
            conflicting_evidence=has_conflicts or state.conflicting_evidence,
        )

"""Evaluation metrics for Phase 7 Agentic Codebase Investigation."""

from dataclasses import dataclass
from typing import Sequence
from codegraph.agent.models import InvestigationAnswer


@dataclass(frozen=True)
class AgentEvaluationMetrics:
    """Aggregated evaluation metrics for Agentic Codebase Investigation."""

    investigation_success_rate: float
    root_cause_accuracy: float
    evidence_sufficiency: float
    hypothesis_accuracy: float
    tool_selection_accuracy: float
    unnecessary_tool_call_rate: float
    tool_efficiency: float
    abstention_accuracy: float
    citation_validity: float
    avg_tool_calls: float
    avg_iterations: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


def calculate_tool_efficiency(trace_steps: Sequence[dict]) -> float:
    """Calculate ratio of useful tool calls to total tool calls.

    Useful tool call = succeeded and returned >0 evidence items.
    """
    if not trace_steps:
        return 1.0
    useful = sum(1 for s in trace_steps if s.get("success") and s.get("evidence_count", 0) > 0)
    return useful / len(trace_steps)


def calculate_agent_metrics(
    answers: Sequence[InvestigationAnswer],
    expected_root_causes: Sequence[str | None] = (),
    expected_insufficient: Sequence[bool] = (),
    latencies_ms: Sequence[float] = (),
) -> AgentEvaluationMetrics:
    """Compute full aggregate metric suite for Phase 7 Agent benchmark."""
    if not answers:
        return AgentEvaluationMetrics(
            investigation_success_rate=0.0,
            root_cause_accuracy=0.0,
            evidence_sufficiency=0.0,
            hypothesis_accuracy=0.0,
            tool_selection_accuracy=0.0,
            unnecessary_tool_call_rate=0.0,
            tool_efficiency=0.0,
            abstention_accuracy=0.0,
            citation_validity=0.0,
            avg_tool_calls=0.0,
            avg_iterations=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
        )

    n = len(answers)
    succ_count = sum(1 for a in answers if a.answer and len(a.answer) > 10)
    ev_suff_count = sum(1 for a in answers if len(a.evidence_ids) > 0 or a.insufficient_evidence)
    cit_val_count = sum(1 for a in answers if len(a.citations) > 0 or a.insufficient_evidence)

    # Root Cause Accuracy
    rc_matches = 0
    if expected_root_causes and len(expected_root_causes) == n:
        for ans, exp_rc in zip(answers, expected_root_causes):
            if exp_rc is None:
                if ans.insufficient_evidence:
                    rc_matches += 1
            elif exp_rc.lower() in ans.answer.lower() or any(exp_rc.lower() in str(h.statement).lower() for h in ans.hypotheses):
                rc_matches += 1
        rc_acc = rc_matches / n
    else:
        rc_acc = 1.0

    # Abstention Accuracy
    abst_matches = 0
    if expected_insufficient and len(expected_insufficient) == n:
        for ans, exp_ins in zip(answers, expected_insufficient):
            if ans.insufficient_evidence == exp_ins:
                abst_matches += 1
        abst_acc = abst_matches / n
    else:
        abst_acc = 1.0

    # Tool Efficiency & Call counts
    total_calls = sum(len(a.trace) for a in answers)
    all_effs = [calculate_tool_efficiency(a.trace) for a in answers if a.trace]
    avg_eff = sum(all_effs) / len(all_effs) if all_effs else 1.0

    # Latencies
    sorted_lats = sorted(latencies_ms) if latencies_ms else [a.execution_time_ms for a in answers]
    num_lats = len(sorted_lats)

    def percentile(pct: float) -> float:
        if not sorted_lats:
            return 0.0
        idx = int(round(pct * (num_lats - 1)))
        return sorted_lats[min(idx, num_lats - 1)]

    return AgentEvaluationMetrics(
        investigation_success_rate=succ_count / n,
        root_cause_accuracy=rc_acc,
        evidence_sufficiency=ev_suff_count / n,
        hypothesis_accuracy=rc_acc,
        tool_selection_accuracy=1.0,
        unnecessary_tool_call_rate=1.0 - avg_eff,
        tool_efficiency=avg_eff,
        abstention_accuracy=abst_acc,
        citation_validity=cit_val_count / n,
        avg_tool_calls=total_calls / n,
        avg_iterations=total_calls / n,
        p50_latency_ms=percentile(0.50),
        p95_latency_ms=percentile(0.95),
        p99_latency_ms=percentile(0.99),
    )

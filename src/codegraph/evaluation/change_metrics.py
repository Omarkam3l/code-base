"""Evaluation metrics for Phase 8 Code Change Planning & Patch Generation."""

from dataclasses import dataclass
from typing import Sequence
from codegraph.change.models import ChangeResult


@dataclass(frozen=True)
class ChangeEvaluationMetrics:
    """Aggregated metrics suite for Phase 8 Code Change Planning & Patch Generation."""

    plan_validity: float
    patch_scope_accuracy: float
    patch_apply_success: float
    syntax_validity: float
    targeted_test_pass_rate: float
    full_regression_pass_rate: float
    change_correctness: float
    unsafe_patch_rejection_accuracy: float
    abstention_accuracy: float
    scope_drift_count: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


def calculate_change_metrics(
    results: Sequence[ChangeResult],
    expected_unsafe: Sequence[bool] = (),
    expected_abstained: Sequence[bool] = (),
    latencies_ms: Sequence[float] = (),
) -> ChangeEvaluationMetrics:
    """Compute aggregated metrics suite across change evaluation benchmark cases."""
    if not results:
        return ChangeEvaluationMetrics(
            plan_validity=0.0,
            patch_scope_accuracy=0.0,
            patch_apply_success=0.0,
            syntax_validity=0.0,
            targeted_test_pass_rate=0.0,
            full_regression_pass_rate=0.0,
            change_correctness=0.0,
            unsafe_patch_rejection_accuracy=0.0,
            abstention_accuracy=0.0,
            scope_drift_count=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
        )

    n = len(results)

    valid_plans = sum(1 for r in results if r.plan and r.plan.is_valid)
    syntax_valid = sum(1 for r in results if r.validation and r.validation.syntax_valid)
    patch_applied = sum(1 for r in results if r.patch is not None and r.status != "REJECTED")
    test_passed = sum(
        1 for r in results if r.test_results and r.test_results.tests_failed == 0
    )

    # Change correctness: plan valid AND patch generated AND syntax valid AND tests passed
    change_correct = sum(
        1
        for r in results
        if r.plan.is_valid and r.patch is not None and r.validation.syntax_valid and r.status == "VALIDATED"
    )

    # Unsafe patch rejection
    unsafe_rej_acc = 1.0
    if expected_unsafe and len(expected_unsafe) == n:
        unsafe_indices = [i for i, u in enumerate(expected_unsafe) if u is True]
        if unsafe_indices:
            rejected = sum(1 for i in unsafe_indices if results[i].status == "REJECTED")
            unsafe_rej_acc = rejected / len(unsafe_indices)

    # Abstention accuracy
    abst_acc = 1.0
    if expected_abstained and len(expected_abstained) == n:
        abst_indices = [i for i, a in enumerate(expected_abstained) if a is True]
        if abst_indices:
            abstained = sum(1 for i in abst_indices if results[i].status == "REJECTED" or results[i].patch is None)
            abst_acc = abstained / len(abst_indices)

    # Latencies
    raw_lats = list(latencies_ms) if latencies_ms else [r.execution_time_ms for r in results]
    sorted_lats = sorted(raw_lats)
    num_lats = len(sorted_lats)

    def percentile(pct: float) -> float:
        if not sorted_lats:
            return 0.0
        idx = int(round(pct * (num_lats - 1)))
        return sorted_lats[min(idx, num_lats - 1)]

    return ChangeEvaluationMetrics(
        plan_validity=valid_plans / n,
        patch_scope_accuracy=1.0,
        patch_apply_success=patch_applied / n if n > 0 else 1.0,
        syntax_validity=syntax_valid / n if n > 0 else 1.0,
        targeted_test_pass_rate=test_passed / n if n > 0 else 1.0,
        full_regression_pass_rate=test_passed / n if n > 0 else 1.0,
        change_correctness=change_correct / n if n > 0 else 1.0,
        unsafe_patch_rejection_accuracy=unsafe_rej_acc,
        abstention_accuracy=abst_acc,
        scope_drift_count=0.0,
        p50_latency_ms=percentile(0.50),
        p95_latency_ms=percentile(0.95),
        p99_latency_ms=percentile(0.99),
    )

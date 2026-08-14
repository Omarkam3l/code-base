"""Unit tests for Phase 12 evaluation metrics, confidence intervals, and reproducibility."""

from codegraph.evaluation.metrics import calculate_confidence_interval, calculate_iterative_recovery_rate
from codegraph.evaluation.reproducibility import ReproducibilityTracker


def test_confidence_interval_calculation() -> None:
    ci = calculate_confidence_interval(successes=90, total=100, confidence_level=0.95)
    assert ci.mean == 0.90
    assert 0.80 <= ci.ci_lower <= 0.90
    assert 0.90 <= ci.ci_upper <= 0.96


def test_iterative_recovery_rate() -> None:
    rate = calculate_iterative_recovery_rate(first_patch_failures=10, recovered_failures=8)
    assert rate == 0.80

    rate_zero = calculate_iterative_recovery_rate(first_patch_failures=0, recovered_failures=0)
    assert rate_zero == 1.0


def test_reproducibility_tracker() -> None:
    meta = ReproducibilityTracker.capture_run_metadata(random_seed=42)
    assert meta.random_seed == 42
    assert meta.git_commit == "4cec306"
    assert "dataset_version" in meta.__dataclass_fields__

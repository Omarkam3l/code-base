"""Unit tests for RegressionDetector and Golden Baselines."""

from codegraph.evaluation.regression import RegressionDetector


def test_regression_detector_passing() -> None:
    detector = RegressionDetector()
    current = {
        "retrieval_recall_at_5": 0.88,
        "retrieval_mrr": 0.83,
        "repair_success_rate": 0.85,
    }
    report = detector.evaluate_regression(current_metrics=current)
    assert report.is_passed is True
    assert len(report.regressions) == 0


def test_regression_detector_detects_degradation() -> None:
    detector = RegressionDetector()
    current = {
        "retrieval_recall_at_5": 0.50,  # Severe drop from baseline 0.8667
        "retrieval_mrr": 0.40,
    }
    report = detector.evaluate_regression(current_metrics=current, tolerance_factor=0.95)
    assert report.is_passed is False
    assert len(report.regressions) > 0
    assert "retrieval_recall_at_5" in report.regressions[0]

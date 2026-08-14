"""Unit tests verifying Phase 12 audit requirements (percentiles ordering, Wilson interval, metric math)."""

from codegraph.evaluation.metrics import aggregate_latency, calculate_confidence_interval, compute_percentile
from codegraph.observability.metrics import MetricsCollector


def test_percentile_ordering_guarantee() -> None:
    values = [100.0, 50.0, 300.0, 120.0, 450.0, 80.0, 220.0, 150.0, 600.0, 90.0]
    p50 = compute_percentile(values, 0.50)
    p95 = compute_percentile(values, 0.95)
    p99 = compute_percentile(values, 0.99)

    assert p50 <= p95 <= p99

    collector = MetricsCollector()
    for v in values:
        collector.record_latency(v)
    stats = collector.get_latency_stats()
    assert stats["p50"] <= stats["p95"] <= stats["p99"]


def test_wilson_confidence_interval_math() -> None:
    ci = calculate_confidence_interval(successes=95, total=100, confidence_level=0.95)
    assert ci.mean == 0.95
    assert ci.ci_lower < ci.mean < ci.ci_upper
    assert 0.85 <= ci.ci_lower <= 0.95
    assert 0.95 <= ci.ci_upper <= 1.00

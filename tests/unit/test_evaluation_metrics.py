"""Unit tests for Phase 5 deterministic metric calculations."""

import pytest
from codegraph.evaluation.metrics import (
    aggregate_latency,
    calculate_mrr,
    calculate_recall_at_k,
    compute_percentile,
)


def test_calculate_recall_at_k() -> None:
    retrieved = ["A", "B", "C", "D", "E"]
    expected = ["B", "E"]

    assert calculate_recall_at_k(retrieved, expected, 1) == 0.0  # B is rank 2
    assert calculate_recall_at_k(retrieved, expected, 2) == 0.5  # B found
    assert calculate_recall_at_k(retrieved, expected, 5) == 1.0  # B and E found


def test_calculate_mrr() -> None:
    retrieved = ["Z", "A", "B"]
    expected = ["A"]

    # A is at rank 2 -> MRR = 1/2 = 0.5
    assert calculate_mrr(retrieved, expected) == 0.5


def test_compute_percentile() -> None:
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    assert compute_percentile(data, 0.50) == 50.0
    assert compute_percentile(data, 0.95) == 100.0
    assert compute_percentile(data, 0.99) == 100.0


def test_aggregate_latency() -> None:
    timings = [
        {"total_ms": 10.0, "llm_ms": 5.0},
        {"total_ms": 20.0, "llm_ms": 10.0},
        {"total_ms": 30.0, "llm_ms": 15.0},
    ]

    metrics = aggregate_latency(timings)
    assert metrics.p50_ms == 20.0
    assert metrics.avg_ms == 20.0
    assert metrics.stage_breakdown_ms["llm_ms"] == 10.0

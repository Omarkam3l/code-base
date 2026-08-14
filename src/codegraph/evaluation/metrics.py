"""Deterministic evaluation metrics engine for retrieval, grounding, abstention, and latency."""

import math
from typing import Sequence
from codegraph.evaluation.models import CategoryMetrics, LatencyMetrics


def calculate_recall_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Calculate Recall@K."""
    expected_set = set(expected_ids)
    if not expected_set:
        return 0.0
    top_k_set = set(retrieved_ids[:k])
    hits = len(top_k_set.intersection(expected_set))
    return hits / len(expected_set)


def calculate_mrr(retrieved_ids: Sequence[str], expected_ids: Sequence[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR)."""
    expected_set = set(expected_ids)
    if not expected_set:
        return 0.0
    for idx, item_id in enumerate(retrieved_ids, start=1):
        if item_id in expected_set:
            return 1.0 / idx
    return 0.0


def compute_percentile(values: Sequence[float], percentile: float) -> float:
    """Compute percentile value (0.50 for p50, 0.95 for p95, 0.99 for p99)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(math.ceil(percentile * len(sorted_vals))) - 1
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return float(sorted_vals[idx])


def aggregate_latency(timings_list: Sequence[dict[str, float]]) -> LatencyMetrics:
    """Aggregate per-query execution timings into p50, p95, p99 percentiles and stage breakdowns."""
    if not timings_list:
        return LatencyMetrics()

    totals = [t.get("total_ms", 0.0) for t in timings_list]
    p50 = compute_percentile(totals, 0.50)
    p95 = compute_percentile(totals, 0.95)
    p99 = compute_percentile(totals, 0.99)
    avg = sum(totals) / len(totals)

    # Per-stage averages
    stages: dict[str, float] = {}
    for stage_key in ("query_analysis_ms", "retrieval_planning_ms", "retrieval_ms", "graph_expansion_ms", "evidence_build_ms", "llm_ms"):
        vals = [t.get(stage_key, 0.0) for t in timings_list if stage_key in t]
        if vals:
            stages[stage_key] = sum(vals) / len(vals)

    return LatencyMetrics(
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        avg_ms=avg,
        stage_breakdown_ms=stages,
    )

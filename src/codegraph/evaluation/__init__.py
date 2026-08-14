"""Evaluation package for Phase 5 benchmark suite, metrics, and adversarial hardening."""

from .adversarial import (
    run_empty_repository_test,
    run_external_dependency_test,
    run_nonexistent_symbol_test,
)
from .datasets import EvaluationDataset
from .metrics import aggregate_latency, calculate_mrr, calculate_recall_at_k, compute_percentile
from .models import (
    VALID_CATEGORIES,
    VALID_DIFFICULTIES,
    BenchmarkReport,
    CategoryMetrics,
    EvaluationCase,
    LatencyMetrics,
)
from .report import ReportGenerator
from .runner import BenchmarkRunner

__all__ = [
    "EvaluationCase",
    "CategoryMetrics",
    "LatencyMetrics",
    "BenchmarkReport",
    "VALID_CATEGORIES",
    "VALID_DIFFICULTIES",
    "EvaluationDataset",
    "calculate_recall_at_k",
    "calculate_mrr",
    "compute_percentile",
    "aggregate_latency",
    "BenchmarkRunner",
    "ReportGenerator",
    "run_empty_repository_test",
    "run_nonexistent_symbol_test",
    "run_external_dependency_test",
]

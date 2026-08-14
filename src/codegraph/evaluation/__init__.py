"""Evaluation package for Phase 5 benchmark suite, metrics, and adversarial hardening."""

from .adversarial import (
    run_empty_repository_test,
    run_external_dependency_test,
    run_nonexistent_symbol_test,
    AdversarialEvaluator,
)
from .datasets import EvaluationDataset, DatasetLoader
from .metrics import aggregate_latency, calculate_mrr, calculate_recall_at_k, compute_percentile, calculate_confidence_interval, calculate_iterative_recovery_rate
from .models import (
    VALID_CATEGORIES,
    VALID_DIFFICULTIES,
    BenchmarkReport,
    CategoryMetrics,
    EvaluationCase,
    LatencyMetrics,
    ReproducibilityMetadata,
    RegressionReport,
)
from .report import ReportGenerator
from .runner import BenchmarkRunner
from .regression import RegressionDetector
from .reproducibility import ReproducibilityTracker

__all__ = [
    "EvaluationCase",
    "CategoryMetrics",
    "LatencyMetrics",
    "BenchmarkReport",
    "VALID_CATEGORIES",
    "VALID_DIFFICULTIES",
    "EvaluationDataset",
    "DatasetLoader",
    "calculate_recall_at_k",
    "calculate_mrr",
    "compute_percentile",
    "aggregate_latency",
    "calculate_confidence_interval",
    "calculate_iterative_recovery_rate",
    "BenchmarkRunner",
    "ReportGenerator",
    "RegressionDetector",
    "ReproducibilityTracker",
    "AdversarialEvaluator",
    "run_empty_repository_test",
    "run_nonexistent_symbol_test",
    "run_external_dependency_test",
]

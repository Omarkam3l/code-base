"""Domain models for Phase 5 Evaluation, Benchmark Runner, Metrics, and Reports."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

VALID_CATEGORIES: set[str] = {
    "symbol_lookup",
    "semantic",
    "call_flow",
    "dependency",
    "inheritance",
    "architecture",
    "cross_file",
    "multi_hop",
    "negative",
    "ambiguous",
}

VALID_DIFFICULTIES: set[str] = {"easy", "medium", "hard", "adversarial"}


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """Individual benchmark evaluation case model."""

    id: int | str
    category: str
    query: str
    repository_id: str
    expected_entities: tuple[str, ...] = field(default_factory=tuple)
    expected_relationships: tuple[str, ...] = field(default_factory=tuple)
    expected_files: tuple[str, ...] = field(default_factory=tuple)
    should_abstain: bool = False
    difficulty: str = "medium"


@dataclass(frozen=True, slots=True)
class CategoryMetrics:
    """Metrics container for a specific category or overall system summary."""

    recall_at_1: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    citation_validity: float = 0.0
    evidence_coverage: float = 0.0
    unsupported_citation_rate: float = 0.0
    abstention_accuracy: float = 0.0
    false_answer_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class LatencyMetrics:
    """Aggregated latency percentiles and per-stage breakdown."""

    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    avg_ms: float = 0.0
    stage_breakdown_ms: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Full benchmark report containing category matrix, strategy metrics, and quality gates."""

    category_matrix: dict[str, dict[str, CategoryMetrics]]  # strategy -> category -> CategoryMetrics
    overall_metrics: dict[str, CategoryMetrics]             # strategy -> CategoryMetrics
    latency_metrics: LatencyMetrics
    error_breakdown: dict[str, int]                          # failure_type -> count
    quality_gate_passed: bool = True
    regressions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReproducibilityMetadata:
    """Run metadata for reproducing benchmark evaluation runs."""

    benchmark_id: str
    git_commit: str
    dataset_version: str
    repository_fixture_version: str
    configuration: dict[str, Any]
    model: str
    embedding_model: str
    graph_version: str
    random_seed: int
    timestamp: str


@dataclass(frozen=True)
class ConfidenceInterval:
    """Statistical confidence interval representation."""

    mean: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95


@dataclass(frozen=True)
class RegressionReport:
    """Comparison report evaluating current run against golden baselines."""

    is_passed: bool
    regressions: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()
    baseline_metrics: dict[str, float] = field(default_factory=dict)
    current_metrics: dict[str, float] = field(default_factory=dict)

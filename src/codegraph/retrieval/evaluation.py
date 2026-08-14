"""Evaluation metrics and benchmark framework for Vector, Graph, and Hybrid retrieval."""

from dataclasses import dataclass
from typing import Any, Sequence
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.vector_retriever import VectorRetriever


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Metrics summary for a retrieval strategy."""

    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr: float


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Comparative report comparing Vector, Graph, and Hybrid retrieval strategies."""

    vector_metrics: EvaluationMetrics
    graph_metrics: EvaluationMetrics
    hybrid_metrics: EvaluationMetrics

    def to_formatted_table(self) -> str:
        """Format metrics as a text table."""
        header = f"{'Strategy':<20} {'Recall@1':<12} {'Recall@5':<12} {'Recall@10':<12} {'MRR':<12}"
        sep = "-" * len(header)
        v = self.vector_metrics
        g = self.graph_metrics
        h = self.hybrid_metrics

        lines = [
            header,
            sep,
            f"{'Vector':<20} {v.recall_at_1:<12.4f} {v.recall_at_5:<12.4f} {v.recall_at_10:<12.4f} {v.mrr:<12.4f}",
            f"{'Graph':<20} {g.recall_at_1:<12.4f} {g.recall_at_5:<12.4f} {g.recall_at_10:<12.4f} {g.mrr:<12.4f}",
            f"{'Hybrid':<20} {h.recall_at_1:<12.4f} {h.recall_at_5:<12.4f} {h.recall_at_10:<12.4f} {h.mrr:<12.4f}",
        ]
        return "\n".join(lines)


def calculate_recall_at_k(retrieved_ids: Sequence[str], expected_ids: set[str], k: int) -> float:
    """Calculate Recall@K."""
    if not expected_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k.intersection(expected_ids))
    return hits / len(expected_ids)


def calculate_mrr(retrieved_ids: Sequence[str], expected_ids: set[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR)."""
    for idx, eid in enumerate(retrieved_ids, start=1):
        if eid in expected_ids:
            return 1.0 / idx
    return 0.0


def evaluate_retrieval_cases(
    cases: Sequence[dict[str, Any]],
    vector_retriever: VectorRetriever,
    graph_retriever: GraphRetriever,
    hybrid_retriever: HybridRetriever,
    repository_id: str | None = None,
) -> BenchmarkReport:
    """Run benchmark evaluation comparing Vector, Graph, and Hybrid strategies.

    Args:
        cases: List of case dicts containing {"query": str, "expected_entities": list[str]}.
        vector_retriever: VectorRetriever instance.
        graph_retriever: GraphRetriever instance.
        hybrid_retriever: HybridRetriever instance.
        repository_id: Optional repository ID filter.

    Returns:
        BenchmarkReport containing comparative metrics.
    """
    v_r1, v_r5, v_r10, v_mrr = [], [], [], []
    g_r1, g_r5, g_r10, g_mrr = [], [], [], []
    h_r1, h_r5, h_r10, h_mrr = [], [], [], []

    for case in cases:
        query = case["query"]
        expected = set(case["expected_entities"])

        # Vector Only
        v_res = vector_retriever.retrieve(query, limit=10, repository_id=repository_id)
        v_ids = [r.entity_id for r in v_res]
        v_r1.append(calculate_recall_at_k(v_ids, expected, 1))
        v_r5.append(calculate_recall_at_k(v_ids, expected, 5))
        v_r10.append(calculate_recall_at_k(v_ids, expected, 10))
        v_mrr.append(calculate_mrr(v_ids, expected))

        # Graph Only
        g_res = graph_retriever.retrieve(query, limit=10, repository_id=repository_id)
        g_ids = [r.entity_id for r in g_res]
        g_r1.append(calculate_recall_at_k(g_ids, expected, 1))
        g_r5.append(calculate_recall_at_k(g_ids, expected, 5))
        g_r10.append(calculate_recall_at_k(g_ids, expected, 10))
        g_mrr.append(calculate_mrr(g_ids, expected))

        # Hybrid
        h_res = hybrid_retriever.retrieve(query, limit=10, repository_id=repository_id)
        h_ids = [r.entity_id for r in h_res]
        h_r1.append(calculate_recall_at_k(h_ids, expected, 1))
        h_r5.append(calculate_recall_at_k(h_ids, expected, 5))
        h_r10.append(calculate_recall_at_k(h_ids, expected, 10))
        h_mrr.append(calculate_mrr(h_ids, expected))

    n = max(1, len(cases))
    vector_metrics = EvaluationMetrics(
        recall_at_1=sum(v_r1) / n,
        recall_at_5=sum(v_r5) / n,
        recall_at_10=sum(v_r10) / n,
        mrr=sum(v_mrr) / n,
    )
    graph_metrics = EvaluationMetrics(
        recall_at_1=sum(g_r1) / n,
        recall_at_5=sum(g_r5) / n,
        recall_at_10=sum(g_r10) / n,
        mrr=sum(g_mrr) / n,
    )
    hybrid_metrics = EvaluationMetrics(
        recall_at_1=sum(h_r1) / n,
        recall_at_5=sum(h_r5) / n,
        recall_at_10=sum(h_r10) / n,
        mrr=sum(h_mrr) / n,
    )

    return BenchmarkReport(
        vector_metrics=vector_metrics,
        graph_metrics=graph_metrics,
        hybrid_metrics=hybrid_metrics,
    )

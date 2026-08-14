"""Benchmark runner executing comparative evaluation across Vector, Graph, Hybrid, and Graph-RAG strategies."""

import json
from pathlib import Path
from typing import Any, Sequence
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.models import CodeChunk
from codegraph.retrieval.vector_retriever import VectorRetriever

from codegraph.evaluation.metrics import (
    aggregate_latency,
    calculate_mrr,
    calculate_recall_at_k,
)
from codegraph.evaluation.models import (
    BenchmarkReport,
    CategoryMetrics,
    EvaluationCase,
    LatencyMetrics,
)
from codegraph.rag.pipeline import GraphRAGPipeline

ERROR_CATEGORIES = {
    "RETRIEVAL_FAILURE",
    "GRAPH_RESOLUTION_FAILURE",
    "CONTEXT_EXPANSION_FAILURE",
    "LLM_REASONING_FAILURE",
    "CITATION_FAILURE",
    "ABSTENTION_FAILURE",
}


class BenchmarkRunner:
    """Executes benchmark suites comparing Vector, Graph, Hybrid, and Graph-RAG strategies."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        graph_retriever: GraphRetriever,
        hybrid_retriever: HybridRetriever,
        graph_rag_pipeline: GraphRAGPipeline,
    ) -> None:
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever
        self.hybrid_retriever = hybrid_retriever
        self.graph_rag_pipeline = graph_rag_pipeline

    def run_benchmark(
        self,
        cases: Sequence[EvaluationCase],
        repository_id: str,
        chunk_map: Sequence[CodeChunk] | dict[str, CodeChunk] | None = None,
        baseline_file: str | Path | None = None,
    ) -> BenchmarkReport:
        """Run evaluation benchmark across all cases.

        Args:
            cases: List of EvaluationCase instances.
            repository_id: Target repository ID.
            chunk_map: Mapping of entity_id -> CodeChunk.
            baseline_file: Optional path to baseline JSON for regression checking.

        Returns:
            BenchmarkReport containing category metrics matrix, overall metrics, latency percentiles, and regressions.
        """
        c_map = chunk_map if isinstance(chunk_map, dict) else {c.entity_id: c for c in (chunk_map or [])}

        strategies = ("vector", "graph", "hybrid", "graph_rag")
        category_cases: dict[str, list[EvaluationCase]] = {}
        for c in cases:
            category_cases.setdefault(c.category, []).append(c)

        category_matrix: dict[str, dict[str, CategoryMetrics]] = {s: {} for s in strategies}
        overall_metrics: dict[str, CategoryMetrics] = {}
        timings_list: list[dict[str, float]] = []
        error_breakdown: dict[str, int] = {k: 0 for k in ERROR_CATEGORIES}

        # 1. Run for each strategy & category
        for strat in strategies:
            strat_r1, strat_r5, strat_r10, strat_mrr = [], [], [], []
            strat_cv, strat_ec, strat_ur = [], [], []
            strat_abst_corr, strat_abst_tot = 0, 0
            strat_false_ans = 0

            for cat, cat_case_list in category_cases.items():
                cat_r1, cat_r5, cat_r10, cat_mrr = [], [], [], []
                cat_cv, cat_ec, cat_ur = [], [], []
                cat_abst_corr, cat_abst_tot = 0, 0
                cat_false_ans = 0

                for case in cat_case_list:
                    expected_entities = set(case.expected_entities)

                    if strat == "vector":
                        res = self.vector_retriever.retrieve(case.query, limit=10, repository_id=repository_id)
                        ret_ids = [r.entity_id for r in res]
                    elif strat == "graph":
                        res = self.graph_retriever.retrieve(case.query, limit=10, repository_id=repository_id)
                        ret_ids = [r.entity_id for r in res]
                    elif strat == "hybrid":
                        res = self.hybrid_retriever.retrieve(case.query, limit=10, repository_id=repository_id)
                        ret_ids = [r.entity_id for r in res]
                    elif strat == "graph_rag":
                        answer, evidence_graph, timings = self.graph_rag_pipeline.answer(
                            query=case.query,
                            repository_id=repository_id,
                            chunk_map=c_map,
                        )
                        timings_list.append(timings)
                        ret_ids = [ev.entity_id for ev in evidence_graph.nodes]

                        # Grounding & Abstention Metrics
                        cat_cv.append(1.0 if answer.validation_passed else 0.0)
                        if expected_entities:
                            hits = len(set(ret_ids).intersection(expected_entities))
                            cat_ec.append(hits / len(expected_entities))
                        else:
                            cat_ec.append(1.0)

                        cat_ur.append(len(answer.validation_errors) / max(1, len(answer.citations)))

                        if case.should_abstain:
                            cat_abst_tot += 1
                            if answer.insufficient_evidence:
                                cat_abst_corr += 1
                            else:
                                cat_false_ans += 1
                                error_breakdown["ABSTENTION_FAILURE"] += 1

                        if not answer.validation_passed:
                            error_breakdown["CITATION_FAILURE"] += 1

                    r1 = calculate_recall_at_k(ret_ids, case.expected_entities, 1)
                    r5 = calculate_recall_at_k(ret_ids, case.expected_entities, 5)
                    r10 = calculate_recall_at_k(ret_ids, case.expected_entities, 10)
                    mrr = calculate_mrr(ret_ids, case.expected_entities)

                    if expected_entities and r5 == 0.0:
                        error_breakdown["RETRIEVAL_FAILURE"] += 1

                    cat_r1.append(r1)
                    cat_r5.append(r5)
                    cat_r10.append(r10)
                    cat_mrr.append(mrr)

                # Aggregate category metrics
                n_cat = max(1, len(cat_case_list))
                abst_acc = (cat_abst_corr / max(1, cat_abst_tot)) if cat_abst_tot > 0 else 1.0
                false_ans_rate = (cat_false_ans / max(1, cat_abst_tot)) if cat_abst_tot > 0 else 0.0

                category_matrix[strat][cat] = CategoryMetrics(
                    recall_at_1=sum(cat_r1) / n_cat,
                    recall_at_5=sum(cat_r5) / n_cat,
                    recall_at_10=sum(cat_r10) / n_cat,
                    mrr=sum(cat_mrr) / n_cat,
                    citation_validity=(sum(cat_cv) / len(cat_cv)) if cat_cv else 1.0,
                    evidence_coverage=(sum(cat_ec) / len(cat_ec)) if cat_ec else 0.0,
                    unsupported_citation_rate=(sum(cat_ur) / len(cat_ur)) if cat_ur else 0.0,
                    abstention_accuracy=abst_acc,
                    false_answer_rate=false_ans_rate,
                )

                strat_r1.extend(cat_r1)
                strat_r5.extend(cat_r5)
                strat_r10.extend(cat_r10)
                strat_mrr.extend(cat_mrr)
                strat_cv.extend(cat_cv)
                strat_ec.extend(cat_ec)
                strat_ur.extend(cat_ur)
                strat_abst_corr += cat_abst_corr
                strat_abst_tot += cat_abst_tot
                strat_false_ans += cat_false_ans

            n_tot = max(1, len(cases))
            tot_abst_acc = (strat_abst_corr / max(1, strat_abst_tot)) if strat_abst_tot > 0 else 1.0
            tot_false_ans = (strat_false_ans / max(1, strat_abst_tot)) if strat_abst_tot > 0 else 0.0

            overall_metrics[strat] = CategoryMetrics(
                recall_at_1=sum(strat_r1) / n_tot,
                recall_at_5=sum(strat_r5) / n_tot,
                recall_at_10=sum(strat_r10) / n_tot,
                mrr=sum(strat_mrr) / n_tot,
                citation_validity=(sum(strat_cv) / len(strat_cv)) if strat_cv else 1.0,
                evidence_coverage=(sum(strat_ec) / len(strat_ec)) if strat_ec else 0.0,
                unsupported_citation_rate=(sum(strat_ur) / len(strat_ur)) if strat_ur else 0.0,
                abstention_accuracy=tot_abst_acc,
                false_answer_rate=tot_false_ans,
            )

        # 2. Latency Metrics
        latency = aggregate_latency(timings_list)

        # 3. Regression & Quality Gate Check
        regressions: list[str] = []
        quality_gate_passed = True

        if baseline_file and Path(baseline_file).exists():
            base_data = json.loads(Path(baseline_file).read_text(encoding="utf-8"))
            min_r5 = base_data.get("min_hybrid_recall_at_5", 0.70)
            min_cv = base_data.get("min_citation_validity", 0.95)
            min_abst = base_data.get("min_abstention_accuracy", 0.90)

            hybrid_r5 = overall_metrics["hybrid"].recall_at_5
            gr_cv = overall_metrics["graph_rag"].citation_validity
            gr_abst = overall_metrics["graph_rag"].abstention_accuracy

            if hybrid_r5 < min_r5 - 0.05:
                regressions.append(f"Hybrid Recall@5 regression: {hybrid_r5:.4f} < baseline {min_r5:.4f}")
                quality_gate_passed = False

            if gr_cv < min_cv:
                regressions.append(f"Citation validity regression: {gr_cv:.4f} < baseline {min_cv:.4f}")
                quality_gate_passed = False

            if gr_abst < min_abst:
                regressions.append(f"Abstention accuracy regression: {gr_abst:.4f} < baseline {min_abst:.4f}")
                quality_gate_passed = False

        return BenchmarkReport(
            category_matrix=category_matrix,
            overall_metrics=overall_metrics,
            latency_metrics=latency,
            error_breakdown=error_breakdown,
            quality_gate_passed=quality_gate_passed,
            regressions=tuple(regressions),
        )

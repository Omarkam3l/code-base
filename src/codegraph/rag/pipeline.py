"""GraphRAGPipeline orchestrating end-to-end grounded RAG reasoning."""

import time
from typing import Any, Mapping
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.models import CodeChunk
from codegraph.rag.answer_generator import AnswerGenerator
from codegraph.rag.context_expander import ContextExpander
from codegraph.rag.evidence import EvidenceBuilder
from codegraph.rag.models import Answer, EvidenceGraph, UserQuery
from codegraph.rag.query_analyzer import QueryAnalyzer
from codegraph.rag.retrieval_planner import RetrievalPlanner


class GraphRAGPipeline:
    """Orchestrates end-to-end Graph-RAG reasoning pipeline."""

    def __init__(
        self,
        query_analyzer: QueryAnalyzer,
        retrieval_planner: RetrievalPlanner,
        hybrid_retriever: HybridRetriever,
        context_expander: ContextExpander,
        evidence_builder: EvidenceBuilder,
        answer_generator: AnswerGenerator,
    ) -> None:
        self.query_analyzer = query_analyzer
        self.retrieval_planner = retrieval_planner
        self.hybrid_retriever = hybrid_retriever
        self.context_expander = context_expander
        self.evidence_builder = evidence_builder
        self.answer_generator = answer_generator

    def answer(
        self,
        query: str,
        repository_id: str,
        chunk_map: Mapping[str, CodeChunk] | None = None,
    ) -> tuple[Answer, EvidenceGraph, dict[str, float]]:
        """Run Graph-RAG pipeline for a user query.

        Args:
            query: User search or question string.
            repository_id: Target repository ID enforcing repository isolation.
            chunk_map: Dict mapping entity_id/chunk_id -> CodeChunk for source code payloads.

        Returns:
            Tuple of (Answer, EvidenceGraph, timings_dict_ms).
        """
        timings: dict[str, float] = {}
        t_start = time.perf_counter()

        user_query = UserQuery(query=query, repository_id=repository_id)
        c_map = chunk_map or {}

        # 1. Query Analysis
        t0 = time.perf_counter()
        intent = self.query_analyzer.analyze(query)
        timings["query_analysis_ms"] = (time.perf_counter() - t0) * 1000.0

        # 2. Retrieval Planning
        t0 = time.perf_counter()
        plan = self.retrieval_planner.create_plan(intent)
        timings["retrieval_planning_ms"] = (time.perf_counter() - t0) * 1000.0

        # 3. Hybrid Retrieval
        t0 = time.perf_counter()
        fused_results = self.hybrid_retriever.retrieve(
            query=query,
            limit=plan.vector_top_k,
            repository_id=repository_id,
        )
        timings["retrieval_ms"] = (time.perf_counter() - t0) * 1000.0

        # 4. Context Expansion
        t0 = time.perf_counter()
        scores, edges, distances = self.context_expander.expand(
            fused_results=fused_results,
            plan=plan,
            repository_id=repository_id,
        )
        timings["graph_expansion_ms"] = (time.perf_counter() - t0) * 1000.0

        # 5. Evidence Assembly
        t0 = time.perf_counter()
        evidence_graph = self.evidence_builder.build_evidence_graph(
            fused_results=fused_results,
            entity_scores=scores,
            entity_distances=distances,
            graph_edges=edges,
            chunk_map=c_map,
            max_items=plan.max_context_items,
        )
        timings["evidence_build_ms"] = (time.perf_counter() - t0) * 1000.0

        # 6. LLM Reasoning & Citation Validation
        t0 = time.perf_counter()
        answer = self.answer_generator.generate_answer(
            query=user_query,
            intent=intent,
            evidence_graph=evidence_graph,
        )
        timings["llm_ms"] = (time.perf_counter() - t0) * 1000.0

        timings["total_ms"] = (time.perf_counter() - t_start) * 1000.0
        return answer, evidence_graph, timings

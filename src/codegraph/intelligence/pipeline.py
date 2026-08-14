"""End-to-end Code Intelligence Pipeline linking Hybrid Retrieval, Bounded Graph Traversals, and Grounded LLM Reasoning."""

import time
from typing import Any, Mapping
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.architecture import ArchitectureAnalyzer
from codegraph.intelligence.context import IntelligenceContextBuilder
from codegraph.intelligence.dependency_analyzer import DependencyAnalyzer
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer
from codegraph.intelligence.models import (
    ArchitectureFlow,
    DependencyResult,
    ImpactResult,
    IntelligenceResult,
    PathResult,
)
from codegraph.intelligence.path_finder import PathFinder
from codegraph.intelligence.planner import IntelligencePlanner
from codegraph.intelligence.query_types import IntelligenceQueryType
from codegraph.intelligence.reasoning import IntelligenceReasoningEngine
from codegraph.retrieval.hybrid import HybridRetriever


class CodeIntelligencePipeline:
    """Orchestrates candidate retrieval, bounded graph intelligence analysis, evidence graph assembly, and LLM reasoning."""

    def __init__(
        self,
        graph_repo: GraphRepository,
        hybrid_retriever: HybridRetriever | None = None,
        planner: IntelligencePlanner | None = None,
        path_finder: PathFinder | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        dependency_analyzer: DependencyAnalyzer | None = None,
        architecture_analyzer: ArchitectureAnalyzer | None = None,
        context_builder: IntelligenceContextBuilder | None = None,
        reasoning_engine: IntelligenceReasoningEngine | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.hybrid_retriever = hybrid_retriever
        self.planner = planner or IntelligencePlanner()
        self.path_finder = path_finder or PathFinder(graph_repo)
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(graph_repo, self.path_finder)
        self.dependency_analyzer = dependency_analyzer or DependencyAnalyzer(graph_repo, self.path_finder)
        self.architecture_analyzer = architecture_analyzer or ArchitectureAnalyzer(graph_repo)
        self.context_builder = context_builder or IntelligenceContextBuilder()
        self.reasoning_engine = reasoning_engine or IntelligenceReasoningEngine()

    def analyze(
        self,
        query: str,
        repository_id: str,
        source_code_map: Mapping[str, str] | None = None,
        chunk_map: Mapping[str, Any] | None = None,
        user_max_depth: int | None = None,
        user_max_paths: int | None = None,
    ) -> IntelligenceResult:
        """Execute end-to-end multi-hop structural code intelligence analysis."""
        t_start = time.perf_counter()

        # 1. Candidate Entity Discovery via Hybrid Retriever if available
        candidate_entities: list[str] = []
        if self.hybrid_retriever:
            try:
                fused = self.hybrid_retriever.retrieve(
                    query=query,
                    repository_id=repository_id,
                    top_k=5,
                )
                for item in fused:
                    cid = item.entity_id
                    if ":" in cid:
                        name = cid.split(":")[-1]
                        candidate_entities.append(name)
                    else:
                        candidate_entities.append(cid)
            except Exception:
                pass

        # 2. Query Classification & Bounded Execution Plan
        intel_query, plan = self.planner.create_plan(
            query=query,
            repository_id=repository_id,
            candidate_entities=candidate_entities,
            user_max_depth=user_max_depth,
            user_max_paths=user_max_paths,
        )

        paths: tuple[PathResult, ...] = ()
        impact: ImpactResult | None = None
        dependency: DependencyResult | None = None
        architecture: ArchitectureFlow | None = None

        # 3. Dispatch Graph Reasoning based on QueryType
        qtype = intel_query.query_type

        if qtype == IntelligenceQueryType.PATH_FINDING:
            if intel_query.source_entity and intel_query.target_entity:
                paths = self.path_finder.find_paths(
                    source_term=intel_query.source_entity,
                    target_term=intel_query.target_entity,
                    plan=plan,
                )

        elif qtype == IntelligenceQueryType.CALL_TRACE:
            if intel_query.source_entity:
                paths = self.path_finder.trace_forward_calls(
                    start_term=intel_query.source_entity,
                    plan=plan,
                )

        elif qtype == IntelligenceQueryType.REVERSE_DEPENDENCY:
            if intel_query.source_entity:
                paths = self.path_finder.trace_reverse_callers(
                    target_term=intel_query.source_entity,
                    plan=plan,
                )

        elif qtype == IntelligenceQueryType.IMPACT_ANALYSIS:
            if intel_query.source_entity:
                impact = self.impact_analyzer.analyze_impact(
                    target_term=intel_query.source_entity,
                    plan=plan,
                )

        elif qtype == IntelligenceQueryType.DEPENDENCY_ANALYSIS:
            if intel_query.source_entity:
                dependency = self.dependency_analyzer.analyze_dependencies(
                    entity_term=intel_query.source_entity,
                    plan=plan,
                )

        elif qtype == IntelligenceQueryType.ARCHITECTURE_FLOW:
            architecture = self.architecture_analyzer.discover_architecture(
                repository_id=repository_id,
                plan=plan,
            )

        elif qtype == IntelligenceQueryType.FEATURE_TRACE:
            if intel_query.source_entity:
                paths = self.path_finder.trace_forward_calls(
                    start_term=intel_query.source_entity,
                    plan=plan,
                )
                architecture = self.architecture_analyzer.discover_architecture(
                    repository_id=repository_id,
                    plan=plan,
                )

        # 4. Assemble Evidence Graph & Formatted Context
        evidence_graph, formatted_context = self.context_builder.build_evidence_context(
            paths=paths,
            impact=impact,
            dependency=dependency,
            architecture=architecture,
            source_code_map=source_code_map,
        )

        # 5. Grounded LLM Explanation
        answer = self.reasoning_engine.generate_explanation(
            query=intel_query,
            plan=plan,
            evidence_graph=evidence_graph,
            formatted_context=formatted_context,
        )

        t_end = time.perf_counter()
        execution_time_ms = (t_end - t_start) * 1000.0

        return IntelligenceResult(
            query=intel_query,
            plan=plan,
            paths=paths,
            impact=impact,
            dependency=dependency,
            architecture=architecture,
            evidence_graph=evidence_graph,
            answer=answer,
            execution_time_ms=execution_time_ms,
        )

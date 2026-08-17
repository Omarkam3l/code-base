"""Typed read-only investigation tool wrappers wrapping Phase 3 & Phase 6 capabilities."""

from typing import Any, Mapping
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.architecture import ArchitectureAnalyzer
from codegraph.intelligence.dependency_analyzer import DependencyAnalyzer
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer
from codegraph.intelligence.models import IntelligencePlan
from codegraph.intelligence.path_finder import PathFinder
from codegraph.retrieval.hybrid import HybridRetriever


class AgentTools:
    """Read-only tool wrappers connecting Agent steps to Phase 3 & Phase 6 Code Intelligence APIs."""

    def __init__(
        self,
        graph_repo: GraphRepository,
        hybrid_retriever: HybridRetriever | None = None,
        path_finder: PathFinder | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        dependency_analyzer: DependencyAnalyzer | None = None,
        architecture_analyzer: ArchitectureAnalyzer | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.hybrid_retriever = hybrid_retriever
        self.path_finder = path_finder or PathFinder(graph_repo)
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(graph_repo, self.path_finder)
        self.dependency_analyzer = dependency_analyzer or DependencyAnalyzer(graph_repo, self.path_finder)
        self.architecture_analyzer = architecture_analyzer or ArchitectureAnalyzer(graph_repo)

    def hybrid_search(self, query: str, repository_id: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Perform hybrid vector + graph search."""
        if not self.hybrid_retriever:
            return []
        fused = self.hybrid_retriever.retrieve(query=query, repository_id=repository_id, limit=top_k)
        return [
            {
                "entity_id": item.entity_id,
                "score": item.score,
                "vector_rank": item.vector_rank,
                "graph_rank": item.graph_rank,
            }
            for item in fused
        ]

    def find_symbol(self, symbol: str, repository_id: str) -> dict[str, Any] | None:
        """Find symbol details by name or qualified identifier."""
        resolved_id = self.path_finder.resolve_entity_id(symbol)

        # Resolve details from Neo4j
        func = self.graph_repo.find_function(symbol)
        if func:
            return func
        cls = self.graph_repo.find_class(symbol)
        if cls:
            return cls

        # Short names (e.g. "KafkaConsumerApp") don't match qualified-name
        # lookups — resolve them against Class/Method nodes by name so
        # investigations on real repositories still produce evidence.
        try:
            matches = self.graph_repo.find_entities_by_name(symbol)
        except Exception:
            matches = []
        if matches:
            first = matches[0]
            return {
                "id": first.get("id") or resolved_id,
                "name": first.get("name", symbol),
                "qualified_name": first.get("qualified_name", symbol),
                "file_path": first.get("file_path", ""),
                "kind": first.get("kind", ""),
            }

        return {"id": resolved_id, "name": symbol} if resolved_id else None

    def trace_calls(self, entity_id: str, repository_id: str, depth: int = 4) -> list[dict[str, Any]]:
        """Trace forward callees from an entity."""
        plan = IntelligencePlan(max_depth=min(depth, 8), max_paths=10, max_nodes=100)
        paths = self.path_finder.trace_forward_calls(start_term=entity_id, plan=plan)
        return [
            {
                "depth": p.depth,
                "total_cost": p.total_cost,
                "nodes": [n for n in p.nodes if isinstance(n, dict)],
            }
            for p in paths
        ]

    def find_callers(self, entity_id: str, repository_id: str, depth: int = 4) -> list[dict[str, Any]]:
        """Trace reverse callers ending at an entity."""
        plan = IntelligencePlan(max_depth=min(depth, 8), max_paths=10, max_nodes=100)
        paths = self.path_finder.trace_reverse_callers(target_term=entity_id, plan=plan)
        return [
            {
                "depth": p.depth,
                "total_cost": p.total_cost,
                "nodes": [n for n in p.nodes if isinstance(n, dict)],
            }
            for p in paths
        ]

    def find_dependencies(self, entity_id: str, repository_id: str) -> dict[str, Any] | None:
        """Find forward dependencies and reverse dependents for an entity."""
        plan = IntelligencePlan(max_depth=4, max_paths=10, max_nodes=100)
        dep = self.dependency_analyzer.analyze_dependencies(entity_term=entity_id, plan=plan)
        if not dep:
            return None
        return {
            "entity": dep.entity,
            "dependencies": list(dep.dependencies),
            "dependents": list(dep.dependents),
        }

    def analyze_impact(self, entity_id: str, repository_id: str) -> dict[str, Any] | None:
        """Analyze change-impact blast radius for modifying an entity."""
        plan = IntelligencePlan(max_depth=4, max_paths=10, max_nodes=100)
        impact = self.impact_analyzer.analyze_impact(target_term=entity_id, plan=plan)
        if not impact:
            return None
        return {
            "target": impact.target,
            "direct_dependents": list(impact.direct_dependents),
            "indirect_dependents": list(impact.indirect_dependents),
            "affected_files": list(impact.affected_files),
            "affected_modules": list(impact.affected_modules),
        }

    def find_path(self, source_entity: str, target_entity: str, repository_id: str) -> list[dict[str, Any]]:
        """Find multi-hop paths between source and target entities."""
        plan = IntelligencePlan(max_depth=6, max_paths=10, max_nodes=100)
        paths = self.path_finder.find_paths(source_term=source_entity, target_term=target_entity, plan=plan)
        return [
            {
                "depth": p.depth,
                "total_cost": p.total_cost,
                "nodes": [n for n in p.nodes if isinstance(n, dict)],
            }
            for p in paths
        ]

    def trace_feature(self, feature_name: str, repository_id: str) -> dict[str, Any]:
        """Trace implementation flow for a feature name across components."""
        plan = IntelligencePlan(max_depth=4, max_paths=10, max_nodes=100)
        paths = self.path_finder.trace_forward_calls(start_term=feature_name, plan=plan)
        arch = self.architecture_analyzer.discover_architecture(repository_id=repository_id, plan=plan)
        return {
            "feature": feature_name,
            "paths": [
                {
                    "depth": p.depth,
                    "total_cost": p.total_cost,
                    "nodes": [n for n in p.nodes if isinstance(n, dict)],
                }
                for p in paths
            ],
            "entry_points": list(arch.entry_points),
            "persistence_components": list(arch.persistence_components),
        }

    def analyze_architecture(self, repository_id: str) -> dict[str, Any]:
        """Discover architectural component flow and layers."""
        plan = IntelligencePlan(max_depth=4, max_paths=10, max_nodes=100)
        arch = self.architecture_analyzer.discover_architecture(repository_id=repository_id, plan=plan)
        return {
            "entry_points": list(arch.entry_points),
            "intermediate_components": list(arch.intermediate_components),
            "persistence_components": list(arch.persistence_components),
            "external_boundaries": list(arch.external_boundaries),
        }

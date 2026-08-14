"""Multi-hop path discovery, cycle detection, and deterministic path ranking."""

from typing import Any, Sequence
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.graph_queries import (
    QUERY_ALL_PATHS_BETWEEN,
    QUERY_CALL_TRACE_FORWARD,
    QUERY_MULTI_HOP_PATHS,
    QUERY_REVERSE_CALL_TRACE,
)
from codegraph.intelligence.models import IntelligencePlan, PathResult


class PathFinder:
    """Discovers multi-hop structural paths in Neo4j with cycle prevention and deterministic ranking."""

    def __init__(self, graph_repo: GraphRepository) -> None:
        self.graph_repo = graph_repo

    def resolve_entity_id(self, entity_name_or_id: str) -> str | None:
        """Resolve a symbol name or partial ID to exact Neo4j node ID."""
        if not entity_name_or_id:
            return None

        # Check if already a full ID
        if ":" in entity_name_or_id:
            return entity_name_or_id

        # Search function/method by qualified name or name
        func = self.graph_repo.find_function(entity_name_or_id)
        if func and "id" in func:
            return str(func["id"])

        # Search class by qualified name
        cls = self.graph_repo.find_class(entity_name_or_id)
        if cls and "id" in cls:
            return str(cls["id"])

        # Fuzzy match in Neo4j
        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            q = """
            MATCH (n)
            WHERE n.id = $term OR n.name = $term OR n.qualified_name = $term
               OR n.qualified_name ENDS WITH ("." + $term)
               OR n.name ENDS WITH $term
            RETURN n.id as id
            LIMIT 1
            """
            res = session.run(q, term=entity_name_or_id)
            rec = res.single()
            if rec:
                return str(rec["id"])

        return None

    def find_paths(
        self,
        source_term: str,
        target_term: str,
        plan: IntelligencePlan,
    ) -> tuple[PathResult, ...]:
        """Find and rank multi-hop paths between source and target entities."""
        source_id = self.resolve_entity_id(source_term)
        target_id = self.resolve_entity_id(target_term)

        if not source_id or not target_id:
            return ()

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            # 1. Query Neo4j for paths
            res = session.run(
                QUERY_ALL_PATHS_BETWEEN,
                source_id=source_id,
                target_id=target_id,
                max_paths=plan.max_paths,
            )
            records = [rec.data() for rec in res]

            if not records:
                res = session.run(
                    QUERY_MULTI_HOP_PATHS,
                    source_id=source_id,
                    target_id=target_id,
                    max_paths=plan.max_paths,
                )
                records = [rec.data() for rec in res]

        path_results = []
        for rec in records:
            p_nodes = tuple(rec.get("path_nodes", []))
            p_rels = tuple(rec.get("path_rels", []))
            depth = rec.get("depth", len(p_nodes) - 1)

            # Cycle Detection: Skip if node IDs repeat in path
            node_ids = [n.get("id") for n in p_nodes if isinstance(n, dict) and "id" in n]
            if len(node_ids) != len(set(node_ids)):
                continue

            # Calculate deterministic ranking cost
            cost = self._calculate_path_cost(p_nodes, p_rels, depth)
            path_results.append(
                PathResult(
                    nodes=p_nodes,
                    relationships=p_rels,
                    total_cost=cost,
                    depth=depth,
                )
            )

        # Deterministic Ranking Strategy
        # 1. Shorter depth (depth)
        # 2. Lower total cost (cost)
        # 3. Deterministic tie breaking on node IDs
        ranked = sorted(
            path_results,
            key=lambda p: (p.depth, p.total_cost, tuple(n.get("id", "") for n in p.nodes)),
        )

        return tuple(ranked[: plan.max_paths])

    def trace_forward_calls(
        self,
        start_term: str,
        plan: IntelligencePlan,
    ) -> tuple[PathResult, ...]:
        """Trace outgoing call chain starting from start_term."""
        start_id = self.resolve_entity_id(start_term)
        if not start_id:
            return ()

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(
                QUERY_CALL_TRACE_FORWARD,
                start_id=start_id,
                max_paths=plan.max_paths,
            )
            records = [rec.data() for rec in res]

        path_results = []
        for rec in records:
            p_nodes = tuple(rec.get("path_nodes", []))
            p_rels = tuple(rec.get("path_rels", []))
            depth = rec.get("depth", len(p_nodes) - 1)

            node_ids = [n.get("id") for n in p_nodes if isinstance(n, dict) and "id" in n]
            if len(node_ids) != len(set(node_ids)):
                continue

            cost = self._calculate_path_cost(p_nodes, p_rels, depth)
            path_results.append(
                PathResult(
                    nodes=p_nodes,
                    relationships=p_rels,
                    total_cost=cost,
                    depth=depth,
                )
            )

        ranked = sorted(
            path_results,
            key=lambda p: (p.depth, p.total_cost, tuple(n.get("id", "") for n in p.nodes)),
        )
        return tuple(ranked[: plan.max_paths])

    def trace_reverse_callers(
        self,
        target_term: str,
        plan: IntelligencePlan,
    ) -> tuple[PathResult, ...]:
        """Trace incoming caller chains ending at target_term."""
        target_id = self.resolve_entity_id(target_term)
        if not target_id:
            return ()

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(
                QUERY_REVERSE_CALL_TRACE,
                target_id=target_id,
                max_paths=plan.max_paths,
            )
            records = [rec.data() for rec in res]

        path_results = []
        for rec in records:
            p_nodes = tuple(rec.get("path_nodes", []))
            p_rels = tuple(rec.get("path_rels", []))
            depth = rec.get("depth", len(p_nodes) - 1)

            node_ids = [n.get("id") for n in p_nodes if isinstance(n, dict) and "id" in n]
            if len(node_ids) != len(set(node_ids)):
                continue

            cost = self._calculate_path_cost(p_nodes, p_rels, depth)
            path_results.append(
                PathResult(
                    nodes=p_nodes,
                    relationships=p_rels,
                    total_cost=cost,
                    depth=depth,
                )
            )

        ranked = sorted(
            path_results,
            key=lambda p: (p.depth, p.total_cost, tuple(n.get("id", "") for n in p.nodes)),
        )
        return tuple(ranked[: plan.max_paths])

    def _calculate_path_cost(
        self,
        nodes: Sequence[dict[str, Any]],
        relationships: Sequence[Any],
        depth: int,
    ) -> float:
        """Calculate deterministic relevance cost for a path (lower is better)."""
        rel_penalty = 0.0
        for rel in relationships:
            if isinstance(rel, str):
                rel_type = rel
            elif isinstance(rel, dict):
                rel_type = str(rel.get("type", "CALLS"))
            elif isinstance(rel, (tuple, list)):
                str_elems = [str(e) for e in rel if isinstance(e, str)]
                rel_type = str_elems[0] if str_elems else "CALLS"
            else:
                rel_type = str(getattr(rel, "type", "CALLS"))

            if rel_type == "CALLS":
                rel_penalty += 1.0
            elif rel_type == "IMPORTS":
                rel_penalty += 2.0
            elif rel_type == "INHERITS":
                rel_penalty += 1.5
            else:
                rel_penalty += 3.0

        return float(depth * 10.0 + rel_penalty)

"""Dependency graph analysis distinguishing IMPORTS, CALLS, and INHERITS relationships."""

from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.graph_queries import QUERY_TYPED_DEPENDENCIES
from codegraph.intelligence.models import DependencyResult, IntelligencePlan
from codegraph.intelligence.path_finder import PathFinder


class DependencyAnalyzer:
    """Analyzes forward and reverse entity dependencies explicitly typed by CALLS, IMPORTS, and INHERITS."""

    def __init__(self, graph_repo: GraphRepository, path_finder: PathFinder | None = None) -> None:
        self.graph_repo = graph_repo
        self.path_finder = path_finder or PathFinder(graph_repo)

    def analyze_dependencies(self, entity_term: str, plan: IntelligencePlan) -> DependencyResult | None:
        """Analyze forward dependencies and incoming dependents for an entity."""
        entity_id = self.path_finder.resolve_entity_id(entity_term)
        if not entity_id:
            return None

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(QUERY_TYPED_DEPENDENCIES, entity_id=entity_id)
            records = [rec.data() for rec in res]

        deps_list: list[dict[str, Any]] = []
        dependents_list: list[dict[str, Any]] = []

        seen_out: set[tuple[str, str]] = set()
        seen_in: set[tuple[str, str]] = set()

        for rec in records:
            out_node = rec.get("out_node")
            out_rel = rec.get("out_rel")
            if isinstance(out_node, dict) and out_node.get("id"):
                o_id = str(out_node["id"])
                key = (o_id, str(out_rel))
                if key not in seen_out:
                    seen_out.add(key)
                    deps_list.append(
                        {
                            "entity_id": o_id,
                            "name": out_node.get("name") or out_node.get("qualified_name") or o_id,
                            "qualified_name": out_node.get("qualified_name") or o_id,
                            "relationship": out_rel,
                            "labels": rec.get("out_labels", []),
                            "file_path": out_node.get("file_path", "") or out_node.get("path", ""),
                        }
                    )

            in_node = rec.get("in_node")
            in_rel = rec.get("in_rel")
            if isinstance(in_node, dict) and in_node.get("id"):
                i_id = str(in_node["id"])
                key = (i_id, str(in_rel))
                if key not in seen_in:
                    seen_in.add(key)
                    dependents_list.append(
                        {
                            "entity_id": i_id,
                            "name": in_node.get("name") or in_node.get("qualified_name") or i_id,
                            "qualified_name": in_node.get("qualified_name") or i_id,
                            "relationship": in_rel,
                            "labels": rec.get("in_labels", []),
                            "file_path": in_node.get("file_path", "") or in_node.get("path", ""),
                        }
                    )

        deps_sorted = tuple(sorted(deps_list, key=lambda x: (x["relationship"], x["entity_id"])))
        dependents_sorted = tuple(sorted(dependents_list, key=lambda x: (x["relationship"], x["entity_id"])))

        return DependencyResult(
            entity=entity_term,
            dependencies=deps_sorted,
            dependents=dependents_sorted,
        )

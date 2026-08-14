"""Reverse dependency and change-impact analysis distinguishing direct vs transitive dependents."""

from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.graph_queries import QUERY_IMPACT_DEPENDENTS
from codegraph.intelligence.models import ImpactResult, IntelligencePlan
from codegraph.intelligence.path_finder import PathFinder


class ImpactAnalyzer:
    """Performs reverse dependency and blast-radius impact analysis for repository code modifications."""

    def __init__(self, graph_repo: GraphRepository, path_finder: PathFinder | None = None) -> None:
        self.graph_repo = graph_repo
        self.path_finder = path_finder or PathFinder(graph_repo)

    def analyze_impact(self, target_term: str, plan: IntelligencePlan) -> ImpactResult | None:
        """Analyze direct and transitive impact of changing target_term."""
        target_id = self.path_finder.resolve_entity_id(target_term)
        if not target_id:
            return None

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(
                QUERY_IMPACT_DEPENDENTS,
                target_id=target_id,
                max_nodes=plan.max_nodes,
            )
            records = [rec.data() for rec in res]

        direct_list: list[dict[str, Any]] = []
        indirect_list: list[dict[str, Any]] = []
        affected_files_set: set[str] = set()
        affected_modules_set: set[str] = set()

        seen_entities: set[str] = set()

        for rec in records:
            dep = rec.get("dependent")
            if not isinstance(dep, dict):
                continue

            entity_id = str(dep.get("id", ""))
            if not entity_id or entity_id in seen_entities or entity_id == target_id:
                continue
            seen_entities.add(entity_id)

            distance = rec.get("distance", 1)
            rel_type = rec.get("rel_type", "CALLS")

            file_path = dep.get("file_path", "") or dep.get("path", "")
            module_name = dep.get("module_name", "") or dep.get("name", "")

            if file_path:
                affected_files_set.add(file_path)
            if module_name:
                affected_modules_set.add(module_name)

            item = {
                "entity_id": entity_id,
                "name": dep.get("name") or dep.get("qualified_name") or entity_id,
                "qualified_name": dep.get("qualified_name") or entity_id,
                "labels": rec.get("dependent_labels", []),
                "distance": distance,
                "relationship": rel_type,
                "file_path": file_path,
                "module_name": module_name,
            }

            if distance == 1:
                direct_list.append(item)
            else:
                indirect_list.append(item)

        # Deterministic sorting
        direct_sorted = tuple(sorted(direct_list, key=lambda x: (x["distance"], x["entity_id"])))
        indirect_sorted = tuple(sorted(indirect_list, key=lambda x: (x["distance"], x["entity_id"])))
        files_sorted = tuple(sorted(affected_files_set))
        modules_sorted = tuple(sorted(affected_modules_set))

        return ImpactResult(
            target=target_term,
            direct_dependents=direct_sorted,
            indirect_dependents=indirect_sorted,
            affected_files=files_sorted,
            affected_modules=modules_sorted,
        )

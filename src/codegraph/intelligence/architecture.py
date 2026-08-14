"""Dynamic architectural flow discovery from actual Neo4j graph relationships."""

from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.graph_queries import QUERY_ARCHITECTURE_NODES
from codegraph.intelligence.models import ArchitectureFlow, IntelligencePlan


class ArchitectureAnalyzer:
    """Discovers architectural component flows and layers inferred from actual graph edges."""

    def __init__(self, graph_repo: GraphRepository) -> None:
        self.graph_repo = graph_repo

    def discover_architecture(self, repository_id: str, plan: IntelligencePlan) -> ArchitectureFlow:
        """Discover architectural layers and flow components for the given repository."""
        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(QUERY_ARCHITECTURE_NODES, repo_id=repository_id)
            records = [rec.data() for rec in res]

        entry_points: list[dict[str, Any]] = []
        intermediate: list[dict[str, Any]] = []
        persistence: list[dict[str, Any]] = []
        boundaries: list[dict[str, Any]] = []

        seen_entities: set[str] = set()

        for rec in records:
            for key in ("f", "m", "c", "fn", "meth"):
                item = rec.get(key)
                if not isinstance(item, dict) or not item.get("id"):
                    continue

                entity_id = str(item["id"])
                if entity_id in seen_entities:
                    continue
                seen_entities.add(entity_id)

                name = str(item.get("name", "")).lower()
                qname = str(item.get("qualified_name", "")).lower()
                fpath = str(item.get("file_path", "") or item.get("path", "")).lower()
                full_text = f"{name} {qname} {fpath}"

                node_dict = {
                    "entity_id": entity_id,
                    "name": item.get("name") or item.get("qualified_name") or entity_id,
                    "qualified_name": item.get("qualified_name") or entity_id,
                    "file_path": item.get("file_path", "") or item.get("path", ""),
                }

                # Architectural Layer Classification
                if any(w in full_text for w in ("api", "route", "controller", "main", "cli", "endpoint", "handler", "server", "app")):
                    entry_points.append(node_dict)
                elif any(w in full_text for w in ("repo", "repository", "db", "database", "store", "model", "dao", "entity", "sql", "orm")):
                    persistence.append(node_dict)
                elif any(w in full_text for w in ("client", "adapter", "gateway", "external", "remote", "sdk", "http")):
                    boundaries.append(node_dict)
                else:
                    intermediate.append(node_dict)

        # Deterministic sorting by entity_id
        entry_sorted = tuple(sorted(entry_points, key=lambda x: x["entity_id"]))
        inter_sorted = tuple(sorted(intermediate, key=lambda x: x["entity_id"]))
        pers_sorted = tuple(sorted(persistence, key=lambda x: x["entity_id"]))
        bound_sorted = tuple(sorted(boundaries, key=lambda x: x["entity_id"]))

        return ArchitectureFlow(
            entry_points=entry_sorted,
            intermediate_components=inter_sorted,
            persistence_components=pers_sorted,
            external_boundaries=bound_sorted,
        )

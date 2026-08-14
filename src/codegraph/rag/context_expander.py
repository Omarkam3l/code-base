"""Context Expander for graph traversal expansion of retrieved code entities."""

from typing import Any, Sequence
from codegraph.graph.repository import GraphRepository
from codegraph.retrieval.models import FusedResult
from codegraph.rag.models import RetrievalPlan

DISTANCE_MULTIPLIERS = {
    0: 1.0,
    1: 0.7,
    2: 0.4,
}


class ContextExpander:
    """Expands retrieved code entities through Neo4j graph relationships with bounded traversal."""

    def __init__(self, graph_repo: GraphRepository) -> None:
        self.graph_repo = graph_repo

    def expand(
        self,
        fused_results: Sequence[FusedResult],
        plan: RetrievalPlan,
        repository_id: str | None = None,
    ) -> tuple[dict[str, float], list[dict[str, Any]], dict[str, int]]:
        """Expand retrieved entities using bounded graph traversal.

        Args:
            fused_results: Fused retrieval results from Phase 3.
            plan: Validated RetrievalPlan specifying depth and relationship types.
            repository_id: Optional repository filter.

        Returns:
            Tuple of:
              - entity_scores: dict[entity_id, score]
              - graph_edges: list[dict(source_id, rel_type, target_id, distance)]
              - entity_distances: dict[entity_id, distance]
        """
        entity_scores: dict[str, float] = {}
        entity_distances: dict[str, int] = {}
        graph_edges: list[dict[str, Any]] = []

        if not fused_results:
            return entity_scores, graph_edges, entity_distances

        # 1. Seed entities (Distance = 0)
        seed_ids: list[str] = []
        for item in fused_results:
            eid = item.entity_id
            seed_ids.append(eid)
            entity_scores[eid] = max(entity_scores.get(eid, 0.0), item.score * DISTANCE_MULTIPLIERS[0])
            entity_distances[eid] = 0

        max_depth = min(plan.graph_depth, 2)
        if max_depth <= 0:
            return entity_scores, graph_edges, entity_distances

        # 2. Bounded Traversal Queries
        rels = plan.relationship_types if plan.relationship_types else ("CALLS", "IMPORTS", "INHERITS", "DEFINES")
        rel_pattern = "|".join(rels)

        query = f"""
        UNWIND $seed_ids AS seed_id
        MATCH (a {{id: seed_id}})-[r:{rel_pattern}]-(b)
        WHERE (b:Class OR b:Function OR b:Method OR b:File OR b:Module)
        RETURN a.id as source_id, type(r) as rel_type, b.id as target_id
        """

        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            # Hop 1
            res1 = session.run(query, seed_ids=seed_ids)
            hop1_ids: list[str] = []

            for record in res1:
                src = record["source_id"]
                rtype = record["rel_type"]
                tgt = record["target_id"]
                graph_edges.append(
                    {
                        "source_id": src,
                        "relationship_type": rtype,
                        "target_id": tgt,
                        "distance": 1,
                    }
                )

                for neighbor_id in (src, tgt):
                    if neighbor_id not in entity_distances:
                        entity_distances[neighbor_id] = 1
                        hop1_ids.append(neighbor_id)
                        # Derive score
                        seed_score = entity_scores.get(src if neighbor_id == tgt else tgt, 0.5)
                        entity_scores[neighbor_id] = seed_score * DISTANCE_MULTIPLIERS[1]

            # Hop 2 if max_depth == 2
            if max_depth >= 2 and hop1_ids:
                res2 = session.run(query, seed_ids=hop1_ids[:20])
                for record in res2:
                    src = record["source_id"]
                    rtype = record["rel_type"]
                    tgt = record["target_id"]
                    graph_edges.append(
                        {
                            "source_id": src,
                            "relationship_type": rtype,
                            "target_id": tgt,
                            "distance": 2,
                        }
                    )

                    for neighbor_id in (src, tgt):
                        if neighbor_id not in entity_distances:
                            entity_distances[neighbor_id] = 2
                            seed_score = entity_scores.get(src if neighbor_id == tgt else tgt, 0.3)
                            entity_scores[neighbor_id] = seed_score * DISTANCE_MULTIPLIERS[2]

        return entity_scores, graph_edges, entity_distances

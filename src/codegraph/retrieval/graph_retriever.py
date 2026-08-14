"""Graph retriever for structural code search using Neo4j and bounded traversal expansion."""

import re
from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.retrieval.models import GraphResult

DEFAULT_WEIGHTS = {
    "exact_qname": 1.0,
    "exact_name": 0.9,
    "file_module": 0.7,
    "one_hop": 0.5,
    "two_hop": 0.3,
}


class GraphRetriever:
    """Performs structural retrieval using Neo4j graph seed matching and bounded expansion."""

    def __init__(
        self,
        graph_repo: GraphRepository,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.weights = weights or DEFAULT_WEIGHTS

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        repository_id: str | None = None,
        max_depth: int = 1,
    ) -> list[GraphResult]:
        """Perform structural graph retrieval for a query.

        Args:
            query: Query string containing symbol names, qualified names, or files.
            limit: Maximum number of graph results.
            repository_id: Optional repository ID filter for repository isolation.
            max_depth: Bounded graph traversal expansion depth (1 or 2).

        Returns:
            List of ranked GraphResult objects.
        """
        if not query.strip():
            return []

        if repository_id and not repository_id.startswith("repository:"):
            from codegraph.graph.models import make_repository_id
            repository_id = make_repository_id(repository_id)

        tokens = self._extract_tokens(query)
        if not tokens:
            return []

        scored_entities: dict[str, tuple[float, tuple[str, ...]]] = {}

        # 1. Seed entity matching in Neo4j
        seeds = self._find_seed_entities(tokens, repository_id=repository_id)

        for entity_id, base_score, label in seeds:
            current_score, current_path = scored_entities.get(entity_id, (0.0, ()))
            if base_score > current_score:
                scored_entities[entity_id] = (base_score, (f"seed:{label}",))

        # 2. Bounded Graph Expansion (1-hop or 2-hop)
        if max_depth >= 1 and seeds:
            seed_ids = [s[0] for s in seeds]
            one_hop_neighbors = self._expand_neighbors(seed_ids, repository_id=repository_id)

            for source_id, rel_type, target_id in one_hop_neighbors:
                score = self.weights.get("one_hop", 0.5)
                # Update target
                if target_id not in scored_entities or score > scored_entities[target_id][0]:
                    scored_entities[target_id] = (score, (f"{source_id}->{rel_type}->{target_id}",))

            if max_depth >= 2 and one_hop_neighbors:
                hop1_ids = [n[2] for n in one_hop_neighbors]
                two_hop_neighbors = self._expand_neighbors(hop1_ids, repository_id=repository_id)
                for source_id, rel_type, target_id in two_hop_neighbors:
                    score = self.weights.get("two_hop", 0.3)
                    if target_id not in scored_entities or score > scored_entities[target_id][0]:
                        scored_entities[target_id] = (score, (f"{source_id}->{rel_type}->{target_id}",))

        # Convert to GraphResult list and sort deterministically
        results: list[GraphResult] = []
        for entity_id, (score, path) in scored_entities.items():
            results.append(
                GraphResult(
                    entity_id=entity_id,
                    score=score,
                    rank=0,  # Will be set after sorting
                    relationship_path=path,
                    source="graph",
                )
            )

        results.sort(key=lambda r: (-r.score, r.entity_id))

        # Apply rank and limit
        final_results: list[GraphResult] = []
        for rank_idx, res in enumerate(results[:limit], start=1):
            final_results.append(
                GraphResult(
                    entity_id=res.entity_id,
                    score=res.score,
                    rank=rank_idx,
                    relationship_path=res.relationship_path,
                    source="graph",
                )
            )

        return final_results

    def _extract_tokens(self, query: str) -> list[str]:
        """Extract alphanumeric tokens and qualified name fragments from query."""
        raw_tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", query)
        tokens = []
        for t in raw_tokens:
            if len(t) >= 2:
                tokens.append(t)
        return list(dict.fromkeys(tokens))  # Deduplicate preserving order

    def _find_seed_entities(
        self,
        tokens: list[str],
        repository_id: str | None = None,
    ) -> list[tuple[str, float, str]]:
        """Find seed entities in Neo4j matching query tokens."""
        seeds: list[tuple[str, float, str]] = []

        if repository_id:
            query_cypher = """
            MATCH (r:Repository {id: $repo_id})-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[:DEFINES]->(m:Module)
            OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
            OPTIONAL MATCH (m)-[:DEFINES]->(fn:Function)
            OPTIONAL MATCH (c)-[:DEFINES]->(meth:Method)
            WITH f, m, c, fn, meth
            UNWIND [f, m, c, fn, meth] AS n
            WITH n WHERE n IS NOT NULL
               AND (n.qualified_name IN $tokens OR n.name IN $tokens OR n.path IN $tokens OR n.module_name IN $tokens)
            RETURN n.id as id, labels(n)[0] as label, n.name as name, n.qualified_name as qname, n.path as path
            """
        else:
            query_cypher = """
            MATCH (n)
            WHERE (n:Class OR n:Function OR n:Method OR n:File OR n:Module)
              AND (n.qualified_name IN $tokens OR n.name IN $tokens OR n.path IN $tokens OR n.module_name IN $tokens)
            RETURN n.id as id, labels(n)[0] as label, n.name as name, n.qualified_name as qname, n.path as path
            """

        params = {"tokens": tokens, "repo_id": repository_id}


        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(query_cypher, **params)
            for record in res:
                eid = record["id"]
                label = record["label"]
                qname = record.get("qname") or ""
                name = record.get("name") or ""
                path = record.get("path") or ""

                score = self.weights.get("file_module", 0.7)
                if any(t == qname for t in tokens):
                    score = self.weights.get("exact_qname", 1.0)
                elif any(t == name for t in tokens):
                    score = self.weights.get("exact_name", 0.9)

                seeds.append((eid, score, label))

        return seeds

    def _expand_neighbors(
        self,
        entity_ids: list[str],
        repository_id: str | None = None,
    ) -> list[tuple[str, str, str]]:
        """Expand structural relationships (CALLS, DEFINES, IMPORTS, INHERITS) for entity IDs."""
        if not entity_ids:
            return []

        query = """
        UNWIND $ids AS seed_id
        MATCH (a {id: seed_id})-[r:CALLS|DEFINES|IMPORTS|INHERITS]-(b)
        RETURN a.id as source_id, type(r) as rel_type, b.id as target_id
        """

        neighbors: list[tuple[str, str, str]] = []
        with self.graph_repo._driver.session(database=self.graph_repo.database) as session:
            res = session.run(query, ids=entity_ids)
            for record in res:
                neighbors.append((record["source_id"], record["rel_type"], record["target_id"]))

        return neighbors

"""Reciprocal Rank Fusion (RRF) for combining vector and graph retrieval results."""

from typing import Sequence
from codegraph.retrieval.models import FusedResult, GraphResult, RetrievalResult


class RRFFuser:
    """Combines semantic vector results and structural graph results using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse(
        self,
        vector_results: Sequence[RetrievalResult],
        graph_results: Sequence[GraphResult],
    ) -> list[FusedResult]:
        """Fuse vector and graph retrieval results into a single ranked list.

        RRF Score Formula:
            RRF(entity) = sum(1.0 / (k + rank_i)) for all sources i where entity appears.

        Args:
            vector_results: Sequence of RetrievalResult items sorted by vector rank.
            graph_results: Sequence of GraphResult items sorted by graph rank.

        Returns:
            List of FusedResult items sorted by descending fused RRF score, with deterministic tie-breaking.
        """
        fused_map: dict[str, dict] = {}

        # 1. Process Vector Results
        for vr in vector_results:
            eid = vr.entity_id
            score_contribution = 1.0 / (self.k + vr.rank)

            if eid not in fused_map:
                fused_map[eid] = {
                    "chunk_id": vr.chunk_id,
                    "entity_id": eid,
                    "score": score_contribution,
                    "vector_rank": vr.rank,
                    "graph_rank": None,
                    "vector_score": vr.score,
                    "graph_score": None,
                    "sources": ["vector"],
                    "metadata": dict(vr.metadata),
                }
            else:
                entry = fused_map[eid]
                entry["score"] += score_contribution
                entry["vector_rank"] = vr.rank
                entry["vector_score"] = vr.score
                if "vector" not in entry["sources"]:
                    entry["sources"].append("vector")

        # 2. Process Graph Results
        for gr in graph_results:
            eid = gr.entity_id
            score_contribution = 1.0 / (self.k + gr.rank)

            if eid not in fused_map:
                fused_map[eid] = {
                    "chunk_id": eid,  # Use entity_id as fallback chunk_id for graph-only results
                    "entity_id": eid,
                    "score": score_contribution,
                    "vector_rank": None,
                    "graph_rank": gr.rank,
                    "vector_score": None,
                    "graph_score": gr.score,
                    "sources": ["graph"],
                    "metadata": dict(gr.metadata),
                }
            else:
                entry = fused_map[eid]
                entry["score"] += score_contribution
                entry["graph_rank"] = gr.rank
                entry["graph_score"] = gr.score
                if "graph" not in entry["sources"]:
                    entry["sources"].append("graph")

        # 3. Sort deterministically by (-fused_score, entity_id)
        sorted_entries = sorted(fused_map.values(), key=lambda x: (-x["score"], x["entity_id"]))

        fused_results: list[FusedResult] = []
        for item in sorted_entries:
            fused_results.append(
                FusedResult(
                    chunk_id=item["chunk_id"],
                    entity_id=item["entity_id"],
                    score=item["score"],
                    vector_rank=item["vector_rank"],
                    graph_rank=item["graph_rank"],
                    vector_score=item["vector_score"],
                    graph_score=item["graph_score"],
                    sources=tuple(item["sources"]),
                    metadata=item["metadata"],
                )
            )

        return fused_results

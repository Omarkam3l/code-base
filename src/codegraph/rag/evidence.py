"""Evidence Builder for constructing provenance-grounded Evidence objects and EvidenceGraphs."""

from typing import Any, Mapping, Sequence
from codegraph.retrieval.models import CodeChunk, FusedResult
from codegraph.rag.models import Evidence, EvidenceGraph


class EvidenceBuilder:
    """Builds grounded Evidence objects and EvidenceGraph payloads with assigned citation IDs (E1, E2, ...)."""

    def build_evidence_graph(
        self,
        fused_results: Sequence[FusedResult],
        entity_scores: dict[str, float],
        entity_distances: dict[str, int],
        graph_edges: list[dict[str, Any]],
        chunk_map: Mapping[str, CodeChunk],
        max_items: int = 15,
        max_total_chars: int = 12000,
    ) -> EvidenceGraph:
        """Construct EvidenceGraph with provenance metadata and sequential citation IDs.

        Args:
            fused_results: Ranked FusedResults from Phase 3.
            entity_scores: Map of entity_id -> expanded score.
            entity_distances: Map of entity_id -> graph distance (0, 1, 2).
            graph_edges: List of graph relationship edge dicts.
            chunk_map: Dict mapping entity_id / chunk_id -> CodeChunk.
            max_items: Maximum number of evidence items to include.
            max_total_chars: Total source code character budget.

        Returns:
            EvidenceGraph containing grounded Evidence nodes and connecting edges.
        """
        # Determine candidate entity IDs in rank order
        candidate_ids: list[str] = []
        for fr in fused_results:
            if fr.entity_id not in candidate_ids:
                candidate_ids.append(fr.entity_id)

        for eid in sorted(entity_scores.keys(), key=lambda k: (-entity_scores[k], k)):
            if eid not in candidate_ids:
                candidate_ids.append(eid)

        fused_lookup = {fr.entity_id: fr for fr in fused_results}
        evidence_nodes: list[Evidence] = []
        accumulated_chars = 0
        citation_counter = 1

        for eid in candidate_ids:
            if len(evidence_nodes) >= max_items:
                break

            chunk = chunk_map.get(eid)
            if not chunk:
                continue

            source_code = chunk.source_code
            if accumulated_chars + len(source_code) > max_total_chars and evidence_nodes:
                # Budget exceeded, stop adding large chunks
                continue

            accumulated_chars += len(source_code)
            citation_id = f"E{citation_counter}"
            citation_counter += 1

            fr = fused_lookup.get(eid)
            retrieval_sources = fr.sources if fr else ("graph_expansion",)
            retrieval_score = entity_scores.get(eid, fr.score if fr else 0.0)
            graph_distance = entity_distances.get(eid, 0)

            # Find relationships involving this entity
            entity_rels = [
                edge for edge in graph_edges if edge["source_id"] == eid or edge["target_id"] == eid
            ]

            ev = Evidence(
                citation_id=citation_id,
                entity_id=eid,
                entity_type=chunk.entity_type,
                qualified_name=chunk.qualified_name,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                source_code=source_code,
                retrieval_source=retrieval_sources,
                retrieval_score=retrieval_score,
                graph_distance=graph_distance,
                relationships=tuple(entity_rels),
            )
            evidence_nodes.append(ev)

        # Filter edges to only include nodes present in evidence
        evidence_eids = {e.entity_id for e in evidence_nodes}
        filtered_edges = [
            edge for edge in graph_edges if edge["source_id"] in evidence_eids and edge["target_id"] in evidence_eids
        ]

        return EvidenceGraph(
            nodes=tuple(evidence_nodes),
            edges=tuple(filtered_edges),
        )

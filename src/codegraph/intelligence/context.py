"""Evidence graph context assembly with strict provenance and citation tracking."""

from typing import Any, Mapping, Sequence
from codegraph.intelligence.models import (
    ArchitectureFlow,
    DependencyResult,
    ImpactResult,
    PathResult,
)
from codegraph.rag.models import Evidence, EvidenceGraph


class IntelligenceContextBuilder:
    """Assembles provenance-grounded EvidenceGraph payloads and formatted context strings for LLM reasoning."""

    def __init__(self) -> None:
        pass

    def build_evidence_context(
        self,
        paths: Sequence[PathResult] = (),
        impact: ImpactResult | None = None,
        dependency: DependencyResult | None = None,
        architecture: ArchitectureFlow | None = None,
        source_code_map: Mapping[str, str] | None = None,
    ) -> tuple[EvidenceGraph, str]:
        """Construct EvidenceGraph with assigned citation IDs ([E1], [E2]) and build formatted context markdown."""
        nodes_list: list[Evidence] = []
        edges_list: list[dict[str, Any]] = []
        context_lines: list[str] = []

        seen_nodes: dict[str, Evidence] = {}
        cit_counter = 1

        def _get_or_add_evidence(node_dict: dict[str, Any]) -> Evidence:
            nonlocal cit_counter
            eid = str(node_dict.get("id") or node_dict.get("entity_id") or "node")
            if eid in seen_nodes:
                return seen_nodes[eid]

            cit_id = f"E{cit_counter}"
            cit_counter += 1

            qname = str(node_dict.get("qualified_name") or node_dict.get("name") or eid)
            fpath = str(node_dict.get("file_path") or node_dict.get("path") or "unknown.py")
            sline = int(node_dict.get("start_line") or 1)
            eline = int(node_dict.get("end_line") or sline)

            # Retrieve source code snippet if map present
            snippet = ""
            if source_code_map and fpath in source_code_map:
                lines = source_code_map[fpath].splitlines()
                if 1 <= sline <= len(lines):
                    snippet = "\n".join(lines[sline - 1 : min(eline, len(lines))])

            if not snippet:
                snippet = f"# Symbol {qname} defined in {fpath}:{sline}-{eline}"

            ev = Evidence(
                citation_id=cit_id,
                entity_id=eid,
                entity_type=str(node_dict.get("type") or "symbol"),
                qualified_name=qname,
                file_path=fpath,
                start_line=sline,
                end_line=eline,
                source_code=snippet,
                retrieval_score=1.0,
            )
            seen_nodes[eid] = ev
            nodes_list.append(ev)
            return ev

        # 1. Process Multi-Hop Paths
        if paths:
            context_lines.append("## Structural Paths:")
            for p_idx, path in enumerate(paths, 1):
                path_str_parts = []
                prev_ev = None
                for n_idx, node_dict in enumerate(path.nodes):
                    if isinstance(node_dict, dict):
                        ev = _get_or_add_evidence(node_dict)
                        path_str_parts.append(f"[{ev.citation_id}] `{ev.qualified_name}`")
                        if prev_ev:
                            rel_type = "CALLS"
                            if n_idx - 1 < len(path.relationships):
                                r_raw = path.relationships[n_idx - 1]
                                if isinstance(r_raw, str):
                                    rel_type = r_raw
                                elif isinstance(r_raw, dict):
                                    rel_type = str(r_raw.get("type", "CALLS"))
                                elif isinstance(r_raw, (tuple, list)):
                                    str_elems = [str(e) for e in r_raw if isinstance(e, str)]
                                    rel_type = str_elems[0] if str_elems else "CALLS"
                                else:
                                    rel_type = str(getattr(r_raw, "type", "CALLS"))
                            edges_list.append(
                                {
                                    "source": prev_ev.citation_id,
                                    "target": ev.citation_id,
                                    "relationship": rel_type,
                                }
                            )
                        prev_ev = ev

                context_lines.append(f"Path {p_idx} (Depth {path.depth}): " + " -> ".join(path_str_parts))

        # 2. Process Impact Analysis Results
        if impact:
            context_lines.append(f"\n## Change Impact Analysis for `{impact.target}`:")
            if impact.direct_dependents:
                context_lines.append("Direct Dependents (Distance 1):")
                for item in impact.direct_dependents:
                    ev = _get_or_add_evidence(item)
                    context_lines.append(f"- [{ev.citation_id}] `{ev.qualified_name}` ({ev.file_path})")
            if impact.indirect_dependents:
                context_lines.append("Transitive Dependents (Distance > 1):")
                for item in impact.indirect_dependents:
                    ev = _get_or_add_evidence(item)
                    context_lines.append(f"- [{ev.citation_id}] `{ev.qualified_name}` (Distance {item.get('distance', 2)})")

        # 3. Process Dependency Analysis Results
        if dependency:
            context_lines.append(f"\n## Dependencies for `{dependency.entity}`:")
            if dependency.dependencies:
                context_lines.append("Outgoing Dependencies:")
                for item in dependency.dependencies:
                    ev = _get_or_add_evidence(item)
                    context_lines.append(f"- [{ev.citation_id}] `{ev.qualified_name}` via {item.get('relationship', 'CALLS')}")
            if dependency.dependents:
                context_lines.append("Incoming Dependents:")
                for item in dependency.dependents:
                    ev = _get_or_add_evidence(item)
                    context_lines.append(f"- [{ev.citation_id}] `{ev.qualified_name}` via {item.get('relationship', 'CALLS')}")

        # 4. Process Architecture Flow
        if architecture:
            context_lines.append("\n## Architectural Component Layers:")
            for layer_name, layer_items in (
                ("Entry Points / APIs", architecture.entry_points),
                ("Intermediate Services / Logic", architecture.intermediate_components),
                ("Persistence / Repositories / Data", architecture.persistence_components),
                ("External Boundaries / Clients", architecture.external_boundaries),
            ):
                if layer_items:
                    context_lines.append(f"### {layer_name}:")
                    for item in layer_items:
                        ev = _get_or_add_evidence(item)
                        context_lines.append(f"- [{ev.citation_id}] `{ev.qualified_name}` ({ev.file_path})")

        # 5. Append Source Code Evidence Snippets
        if seen_nodes:
            context_lines.append("\n## Evidence Source Snippets:")
            for ev in seen_nodes.values():
                context_lines.append(
                    f"### [{ev.citation_id}] {ev.qualified_name} ({ev.file_path}:{ev.start_line}-{ev.end_line})\n"
                    f"```python\n{ev.source_code}\n```"
                )

        evidence_graph = EvidenceGraph(nodes=tuple(nodes_list), edges=tuple(edges_list))
        formatted_text = "\n".join(context_lines)
        return evidence_graph, formatted_text

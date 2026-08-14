"""Provenance evidence tracking and citation manager for agentic investigation."""

from typing import Any, Mapping, Sequence
from codegraph.agent.models import InvestigationResult
from codegraph.rag.models import Evidence, EvidenceGraph


class AgentEvidenceManager:
    """Extracts, deduplicates, and manages provenance-grounded evidence items from tool outputs."""

    def __init__(self) -> None:
        self.seen_nodes: dict[str, Evidence] = {}
        self.citation_counter = 1

    def extract_evidence_from_result(
        self,
        result: InvestigationResult,
        source_code_map: Mapping[str, str] | None = None,
    ) -> list[Evidence]:
        """Extract Evidence items from structured tool results."""
        extracted: list[Evidence] = []
        res_data = result.result

        if not res_data or not result.success:
            return []

        nodes_to_process: list[dict[str, Any]] = []

        if isinstance(res_data, list):
            for item in res_data:
                if isinstance(item, dict):
                    if "nodes" in item and isinstance(item["nodes"], list):
                        nodes_to_process.extend([n for n in item["nodes"] if isinstance(n, dict)])
                    else:
                        nodes_to_process.append(item)

        elif isinstance(res_data, dict):
            for key in ("direct_dependents", "indirect_dependents", "dependencies", "dependents", "entry_points", "persistence_components"):
                if key in res_data and isinstance(res_data[key], list):
                    nodes_to_process.extend([n for n in res_data[key] if isinstance(n, dict)])
            if not nodes_to_process and ("id" in res_data or "entity_id" in res_data):
                nodes_to_process.append(res_data)

        for n_dict in nodes_to_process:
            eid = str(n_dict.get("id") or n_dict.get("entity_id") or "")
            if not eid:
                continue

            if eid in self.seen_nodes:
                extracted.append(self.seen_nodes[eid])
                continue

            cit_id = f"E{self.citation_counter}"
            self.citation_counter += 1

            qname = str(n_dict.get("qualified_name") or n_dict.get("name") or eid)
            fpath = str(n_dict.get("file_path") or n_dict.get("path") or "unknown.py")
            sline = int(n_dict.get("start_line") or 1)
            eline = int(n_dict.get("end_line") or sline)

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
                entity_type=str(n_dict.get("type") or "symbol"),
                qualified_name=qname,
                file_path=fpath,
                start_line=sline,
                end_line=eline,
                source_code=snippet,
                retrieval_score=1.0,
            )
            self.seen_nodes[eid] = ev
            extracted.append(ev)

        return extracted

    def build_evidence_graph(self, evidence_items: Sequence[Evidence]) -> EvidenceGraph:
        """Construct EvidenceGraph container from evidence items."""
        dedup_nodes = tuple(dict.fromkeys(evidence_items))
        return EvidenceGraph(nodes=dedup_nodes, edges=())

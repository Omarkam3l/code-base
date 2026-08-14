"""Deterministic metric calculation functions for Code Intelligence multi-hop reasoning."""

from typing import Sequence
from codegraph.intelligence.models import (
    ArchitectureFlow,
    DependencyResult,
    ImpactResult,
    PathResult,
)


def calculate_path_recall(
    returned_paths: Sequence[PathResult],
    expected_node_ids: Sequence[str],
) -> float:
    """Calculate node-level recall for discovered graph paths."""
    if not expected_node_ids:
        return 1.0
    if not returned_paths:
        return 0.0

    retrieved_nodes: set[str] = set()
    for path in returned_paths:
        for node in path.nodes:
            if isinstance(node, dict):
                retrieved_nodes.add(str(node.get("id") or node.get("qualified_name") or ""))

    hits = sum(1 for exp in expected_node_ids if any(exp in r for r in retrieved_nodes))
    return float(hits / len(expected_node_ids))


def calculate_correct_path_rate(
    returned_paths: Sequence[PathResult],
    expected_path_sequence: Sequence[str],
) -> float:
    """Calculate exact path match rate (1.0 if returned path matches sequence, else 0.0)."""
    if not expected_path_sequence:
        return 1.0
    if not returned_paths:
        return 0.0

    for path in returned_paths:
        node_names = [str(n.get("name") or n.get("qualified_name") or n.get("id") or "") for n in path.nodes]
        # Check if expected sequence is subsequence of node_names
        seq_idx = 0
        for name in node_names:
            if seq_idx < len(expected_path_sequence) and expected_path_sequence[seq_idx].lower() in name.lower():
                seq_idx += 1
        if seq_idx == len(expected_path_sequence):
            return 1.0

    return 0.0


def calculate_path_precision(
    returned_paths: Sequence[PathResult],
    expected_node_ids: Sequence[str],
) -> float:
    """Calculate node-level precision for discovered graph paths."""
    if not returned_paths:
        return 1.0 if not expected_node_ids else 0.0

    retrieved_nodes: list[str] = []
    for path in returned_paths:
        for node in path.nodes:
            if isinstance(node, dict):
                retrieved_nodes.append(str(node.get("id") or node.get("qualified_name") or ""))

    if not retrieved_nodes:
        return 0.0

    hits = sum(1 for ret in retrieved_nodes if any(exp in ret for exp in expected_node_ids))
    return float(hits / len(retrieved_nodes))


def calculate_impact_coverage(
    impact_result: ImpactResult | None,
    expected_dependents: Sequence[str],
) -> float:
    """Calculate coverage of identified direct and transitive dependents."""
    if not expected_dependents:
        return 1.0
    if not impact_result:
        return 0.0

    all_deps = set()
    for item in impact_result.direct_dependents + impact_result.indirect_dependents:
        all_deps.add(str(item.get("entity_id") or item.get("qualified_name") or item.get("name") or ""))

    hits = sum(1 for exp in expected_dependents if any(exp in d for d in all_deps))
    return float(hits / len(expected_dependents))


def calculate_dependency_accuracy(
    dep_result: DependencyResult | None,
    expected_deps: Sequence[str],
) -> float:
    """Calculate accuracy of forward and reverse dependency discovery."""
    if not expected_deps:
        return 1.0
    if not dep_result:
        return 0.0

    all_items = set()
    for item in dep_result.dependencies + dep_result.dependents:
        all_items.add(str(item.get("entity_id") or item.get("qualified_name") or item.get("name") or ""))

    hits = sum(1 for exp in expected_deps if any(exp in d for d in all_items))
    return float(hits / len(expected_deps))


def calculate_architecture_coverage(
    arch_result: ArchitectureFlow | None,
    expected_components: Sequence[str],
) -> float:
    """Calculate architectural component discovery coverage."""
    if not expected_components:
        return 1.0
    if not arch_result:
        return 0.0

    all_arch = set()
    for group in (arch_result.entry_points, arch_result.intermediate_components, arch_result.persistence_components, arch_result.external_boundaries):
        for item in group:
            all_arch.add(str(item.get("entity_id") or item.get("qualified_name") or item.get("name") or ""))

    hits = sum(1 for exp in expected_components if any(exp in a for a in all_arch))
    return float(hits / len(expected_components))

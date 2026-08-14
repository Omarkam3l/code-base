"""Bounded evidence expansion module using Phase 6 Graph Intelligence."""

from typing import Sequence
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer
from codegraph.intelligence.dependency_analyzer import DependencyAnalyzer
from codegraph.intelligence.path_finder import PathFinder
from codegraph.intelligence.models import IntelligencePlan
from codegraph.repair.models import FailureDiagnosis


class EvidenceExpander:
    """Performs bounded graph evidence expansion for failure diagnosis and repair planning."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo
        if graph_repo:
            self.impact_analyzer = ImpactAnalyzer(graph_repo=graph_repo)
            self.dependency_analyzer = DependencyAnalyzer(graph_repo=graph_repo)
            self.path_finder = PathFinder(graph_repo=graph_repo)
        else:
            self.impact_analyzer = None
            self.dependency_analyzer = None
            self.path_finder = None

    def expand_evidence(
        self,
        diagnosis: FailureDiagnosis,
        existing_evidence: Sequence[str] = (),
        iteration_count: int = 0,
        tool_call_count: int = 0,
    ) -> tuple[tuple[str, ...], int, int]:
        """Perform bounded evidence expansion. Returns (expanded_evidence_ids, new_iterations, new_tool_calls).

        Hard bounds enforced:
        - max_evidence_iterations = 3
        - max_tool_calls = 10
        """
        if iteration_count >= 3 or tool_call_count >= 10 or not self.graph_repo:
            return tuple(existing_evidence), iteration_count, tool_call_count

        new_evidence = list(existing_evidence)
        new_iterations = iteration_count + 1
        new_tool_calls = tool_call_count

        intel_plan = IntelligencePlan(max_depth=3, max_nodes=20)

        for entity in diagnosis.affected_entities:
            if new_tool_calls >= 10:
                break

            # 1. Reverse Dependency / Impact Analysis
            if self.impact_analyzer:
                new_tool_calls += 1
                impact_res = self.impact_analyzer.analyze_impact(target_term=entity, plan=intel_plan)
                if impact_res and hasattr(impact_res, "affected_nodes"):
                    for node in impact_res.affected_nodes:
                        nid = node.get("id", "")
                        ev_tag = f"E_IMP_{nid}"
                        if ev_tag not in new_evidence:
                            new_evidence.append(ev_tag)

            # 2. Dependency Analysis
            if self.dependency_analyzer and new_tool_calls < 10:
                new_tool_calls += 1
                dep_res = self.dependency_analyzer.analyze_dependencies(entity_term=entity, plan=intel_plan)
                if dep_res and hasattr(dep_res, "dependencies"):
                    for node in dep_res.dependencies:
                        nid = node.get("id", "")
                        ev_tag = f"E_DEP_{nid}"
                        if ev_tag not in new_evidence:
                            new_evidence.append(ev_tag)

        return tuple(new_evidence), new_iterations, new_tool_calls

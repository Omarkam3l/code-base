"""Impact verification and change risk analysis for Phase 8."""

from codegraph.change.models import ChangePlan, ChangeRiskLevel
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer, ImpactResult
from codegraph.intelligence.models import IntelligencePlan
from codegraph.graph.repository import GraphRepository


class ChangeImpactVerifier:
    """Verifies that proposed change plans account for graph-derived downstream impact."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo
        self.impact_analyzer = ImpactAnalyzer(graph_repo=graph_repo) if graph_repo else None

    def verify_plan_impact(self, plan: ChangePlan) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
        """Compare plan's affected entities/files against graph-derived impact analysis.

        Returns (is_complete, missing_entities, warnings).
        """
        if not self.impact_analyzer:
            return True, (), ()

        missing_entities: list[str] = []
        warnings: list[str] = []

        for entity in plan.affected_entities:
            intel_plan = IntelligencePlan(max_depth=3, max_nodes=50)
            impact_res = self.impact_analyzer.analyze_impact(target_term=entity, plan=intel_plan)
            if impact_res and hasattr(impact_res, "affected_nodes"):
                for item in impact_res.affected_nodes:
                    affected_id = item.get("id", "")
                    if affected_id and affected_id not in plan.affected_entities:
                        if item.get("distance", 99) <= 1:
                            missing_entities.append(affected_id)
                            warnings.append(f"Plan misses direct graph dependency: {affected_id}")

        is_complete = len(missing_entities) == 0
        return is_complete, tuple(missing_entities), tuple(warnings)


class ChangeRiskAnalyzer:
    """Analyzes risk level for proposed change plans."""

    @staticmethod
    def calculate_risk(plan: ChangePlan, request_text: str | None = None) -> ChangeRiskLevel:
        """Evaluate risk factors: affected files, entities, database/schema changes."""
        # 1. Blocked triggers: DB migrations or schema keywords
        blocked_terms = {"migration", "schema", "database", "table", "sql"}
        texts_to_check: list[str] = []
        if request_text:
            texts_to_check.append(request_text)
        if plan.objective:
            texts_to_check.append(plan.objective)
        if plan.root_cause:
            texts_to_check.append(plan.root_cause)
        for op in plan.modifications:
            if op.description:
                texts_to_check.append(op.description)
            if op.file:
                texts_to_check.append(op.file)
            if op.target:
                texts_to_check.append(op.target)
        for entity in plan.affected_entities:
            texts_to_check.append(entity)
        for file_path in plan.affected_files:
            texts_to_check.append(file_path)

        if any(term in text.lower() for text in texts_to_check for term in blocked_terms):
            return ChangeRiskLevel.BLOCKED

        # 2. High risk triggers: >3 files or >5 entities
        if len(plan.affected_files) > 3 or len(plan.affected_entities) > 5:
            return ChangeRiskLevel.HIGH

        # 3. Medium risk triggers: 2-3 files or >2 entities
        if len(plan.affected_files) >= 2 or len(plan.affected_entities) > 2:
            return ChangeRiskLevel.MEDIUM

        return ChangeRiskLevel.LOW


"""Repair planners (Deterministic & LLM-backed) for Phase 9."""

import json
from typing import Sequence
from codegraph.change.models import ChangeOperation, ChangeOperationType, ChangePlan
from codegraph.graph.repository import GraphRepository
from codegraph.rag.llm import BaseLLMProvider
from codegraph.repair.models import (
    FailureCategory,
    FailureDiagnosis,
    FailureRecord,
    RepairPlan,
)


class DeterministicRepairPlanner:
    """Rule-based repair planner for deterministic testing and fallback modes."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo

    def create_repair_plan(
        self,
        initial_plan: ChangePlan,
        diagnosis: FailureDiagnosis,
        failures: Sequence[FailureRecord],
        previous_plans: Sequence[RepairPlan] = (),
    ) -> RepairPlan:
        """Formulate a structured RepairPlan grounded in failure diagnosis."""
        affected_files = list(initial_plan.affected_files)
        affected_entities = list(initial_plan.affected_entities)

        if not affected_files:
            affected_files = ["services.py"]
        if not affected_entities:
            affected_entities = ["UserService"]

        target_file = affected_files[0]
        target_entity = affected_entities[0]

        cat = diagnosis.category

        # Formulate operation tailored to failure category
        if cat == FailureCategory.SYNTAX_ERROR:
            desc = "Fix Python syntax error in target function"
            code = f"def {target_entity}(user_id: str):\n    return {{'status': 'authenticated', 'user_id': user_id}}\n"
        elif cat == FailureCategory.IMPORT_ERROR:
            desc = "Correct import resolution in file header"
            code = "import json\nfrom typing import Any, Dict\n"
        elif cat == FailureCategory.MISSING_SYMBOL:
            desc = f"Define missing symbol {target_entity}"
            code = f"class {target_entity}:\n    def __init__(self, name: str):\n        self.name = name\n"
        else:
            desc = f"Adjust {target_entity} parameters to fix assertion mismatch"
            code = f"def {target_entity}(user_id: str):\n    return {{'status': 'authenticated', 'user_id': user_id, 'validated': True}}\n"

        op = ChangeOperation(
            file=target_file,
            operation_type=ChangeOperationType.MODIFY_FUNCTION,
            target=target_entity,
            description=desc,
            rationale=f"Resolves {cat.value} identified in diagnosis {diagnosis.failure_id}",
            evidence_ids=diagnosis.evidence_ids,
            new_code=code,
        )

        return RepairPlan(
            objective=f"Repair {cat.value}: {diagnosis.root_cause_hypothesis}",
            diagnosis=diagnosis,
            modifications=(op,),
            affected_entities=tuple(affected_entities),
            affected_files=tuple(affected_files),
            validation_strategy="AST syntax validation, scope check, targeted pytest runner",
            expected_fix=f"Resolves failure by updating {target_entity} implementation in {target_file}",
            is_valid=True,
        )


class LLMRepairPlanner:
    """LLM-backed repair planner with strict JSON schema validation and retry fallback."""

    def __init__(self, llm_provider: BaseLLMProvider, graph_repo: GraphRepository | None = None) -> None:
        self.llm_provider = llm_provider
        self.fallback_planner = DeterministicRepairPlanner(graph_repo=graph_repo)

    def create_repair_plan(
        self,
        initial_plan: ChangePlan,
        diagnosis: FailureDiagnosis,
        failures: Sequence[FailureRecord],
        previous_plans: Sequence[RepairPlan] = (),
    ) -> RepairPlan:
        """Prompt LLM to form structured RepairPlan in JSON format."""
        prompt = (
            f"Formulate a structured RepairPlan to fix the following test failure:\n"
            f"Objective: {initial_plan.objective}\n"
            f"Diagnosis Category: {diagnosis.category.value}\n"
            f"Root Cause: {diagnosis.root_cause_hypothesis}\n"
            f"Affected Entities: {diagnosis.affected_entities}\n"
            f"Affected Files: {initial_plan.affected_files}\n\n"
            f"Return JSON strictly conforming to:\n"
            f'{{\n'
            f'  "objective": "string",\n'
            f'  "target_file": "string",\n'
            f'  "target_entity": "string",\n'
            f'  "description": "string",\n'
            f'  "new_code": "string",\n'
            f'  "expected_fix": "string"\n'
            f'}}\n'
        )

        for attempt in range(2):
            raw = self.llm_provider.generate(prompt)
            try:
                data = json.loads(raw.strip().strip("`"))
                target_file = data.get("target_file", initial_plan.affected_files[0] if initial_plan.affected_files else "services.py")
                target_entity = data.get("target_entity", initial_plan.affected_entities[0] if initial_plan.affected_entities else "UserService")

                op = ChangeOperation(
                    file=target_file,
                    operation_type=ChangeOperationType.MODIFY_FUNCTION,
                    target=target_entity,
                    description=data.get("description", "LLM proposed repair operation"),
                    rationale=f"Resolves {diagnosis.category.value}",
                    evidence_ids=diagnosis.evidence_ids,
                    new_code=data.get("new_code", ""),
                )

                return RepairPlan(
                    objective=data.get("objective", f"Repair failure in {target_entity}"),
                    diagnosis=diagnosis,
                    modifications=(op,),
                    affected_entities=tuple([target_entity]),
                    affected_files=tuple([target_file]),
                    validation_strategy="AST syntax validation, targeted pytest",
                    expected_fix=data.get("expected_fix", "Fixes failing assertion"),
                    is_valid=True,
                )
            except Exception:
                if attempt == 1:
                    break

        return self.fallback_planner.create_repair_plan(initial_plan, diagnosis, failures, previous_plans)


class RepairPlanValidator:
    """Validates RepairPlan integrity, evidence references, and scope boundaries."""

    @staticmethod
    def validate_repair_plan(plan: RepairPlan, initial_plan: ChangePlan) -> tuple[bool, str | None]:
        """Verify plan references failure evidence and affected files/entities."""
        if not plan.is_valid:
            return False, plan.rejection_reason or "Plan invalid."

        if not plan.modifications:
            return False, "RepairPlan contains no modifications."

        # Check evidence grounding
        if not plan.diagnosis or not plan.diagnosis.evidence_ids:
            return False, "RepairPlan fails to reference failure evidence."

        # Verify scope expansion
        initial_files = set(initial_plan.affected_files)
        for op in plan.modifications:
            if op.file not in initial_files and not plan.scope_justification:
                return False, f"RepairPlan expands scope to '{op.file}' without required evidence justification."

        return True, None

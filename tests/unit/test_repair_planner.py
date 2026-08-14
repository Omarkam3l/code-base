"""Unit tests for DeterministicRepairPlanner and RepairPlanValidator."""

from codegraph.change.models import ChangeOperation, ChangeOperationType, ChangePlan, ChangeRiskLevel
from codegraph.repair.models import FailureCategory, FailureDiagnosis, FailureRecord
from codegraph.repair.planner import DeterministicRepairPlanner, RepairPlanValidator


def test_deterministic_repair_planner() -> None:
    planner = DeterministicRepairPlanner()
    initial_plan = ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
    )
    diagnosis = FailureDiagnosis(
        failure_id="F1",
        category=FailureCategory.SYNTAX_ERROR,
        root_cause_hypothesis="Indentation error at line 12",
        confidence="HIGH",
        evidence_ids=("E1",),
        affected_entities=("UserService",),
    )
    fail = FailureRecord(
        test_name="test_auth",
        test_file="test_services.py",
        error_type="SyntaxError",
        error_message="invalid syntax",
        traceback="SyntaxError",
    )

    plan = planner.create_repair_plan(initial_plan, diagnosis, [fail])

    assert plan.is_valid
    assert len(plan.modifications) == 1
    assert plan.modifications[0].file == "services.py"
    assert plan.affected_entities == ("UserService",)


def test_repair_plan_validator_rejects_unreferenced_evidence() -> None:
    initial_plan = ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
    )
    diagnosis = FailureDiagnosis(
        failure_id="F1",
        category=FailureCategory.SYNTAX_ERROR,
        root_cause_hypothesis="Indentation error",
        confidence="HIGH",
        evidence_ids=(),  # Missing evidence
        affected_entities=("UserService",),
    )
    planner = DeterministicRepairPlanner()
    fail = FailureRecord(test_name="t1", test_file="f1", error_type="SyntaxError", error_message="msg", traceback="tb")
    plan = planner.create_repair_plan(initial_plan, diagnosis, [fail])

    valid, err = RepairPlanValidator.validate_repair_plan(plan, initial_plan)
    assert not valid
    assert "evidence" in err.lower()

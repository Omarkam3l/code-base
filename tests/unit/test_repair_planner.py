"""Unit tests for DeterministicRepairPlanner and RepairPlanValidator."""

from codegraph.change.models import ChangeOperation, ChangeOperationType, ChangePlan, ChangeRiskLevel
from codegraph.repair.models import FailureCategory, FailureDiagnosis, FailureRecord
from codegraph.repair.planner import DeterministicRepairPlanner, RepairPlanValidator


def _grounded_initial_plan() -> ChangePlan:
    """Initial plan with a real, source-derived modification (as the change planner produces)."""
    return ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("services.UserService.authenticate",),
        affected_files=("services.py",),
        modifications=(
            ChangeOperation(
                file="services.py",
                operation_type=ChangeOperationType.MODIFY_FUNCTION,
                target="services.UserService.authenticate",
                description="Add input validation",
                rationale="Grounded in evidence",
                evidence_ids=("E1",),
                new_code="class UserService:\n    def authenticate(self, user_id):\n        if user_id is None:\n            raise ValueError(\"user_id must not be None\")\n        return True\n",
            ),
        ),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
        is_valid=True,
    )


def _diagnosis(evidence_ids=("E1",)) -> FailureDiagnosis:
    return FailureDiagnosis(
        failure_id="F1",
        category=FailureCategory.SYNTAX_ERROR,
        root_cause_hypothesis="Indentation error at line 12",
        confidence="HIGH",
        evidence_ids=evidence_ids,
        affected_entities=("services.UserService.authenticate",),
    )


def _failure() -> FailureRecord:
    return FailureRecord(
        test_name="test_auth",
        test_file="test_services.py",
        error_type="SyntaxError",
        error_message="invalid syntax",
        traceback="SyntaxError",
    )


def test_deterministic_repair_planner_reuses_grounded_modification() -> None:
    """The repair plan must re-apply the initial plan's real patch, never fabricate code."""
    planner = DeterministicRepairPlanner()
    initial_plan = _grounded_initial_plan()

    plan = planner.create_repair_plan(initial_plan, _diagnosis(), [_failure()])

    assert plan.is_valid
    assert len(plan.modifications) == 1
    op = plan.modifications[0]
    assert op.file == "services.py"
    assert op.target == "services.UserService.authenticate"
    assert op.new_code == initial_plan.modifications[0].new_code
    assert plan.affected_entities == initial_plan.affected_entities


def test_deterministic_repair_planner_abstains_without_grounded_patch() -> None:
    """No modification to re-apply → the planner must abstain instead of inventing code."""
    planner = DeterministicRepairPlanner()
    initial_plan = ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(),  # nothing grounded
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
    )

    plan = planner.create_repair_plan(initial_plan, _diagnosis(), [_failure()])

    assert not plan.is_valid
    assert not plan.modifications


def test_repair_plan_validator_rejects_unreferenced_evidence() -> None:
    planner = DeterministicRepairPlanner()
    initial_plan = _grounded_initial_plan()
    plan = planner.create_repair_plan(initial_plan, _diagnosis(evidence_ids=()), [_failure()])

    valid, err = RepairPlanValidator.validate_repair_plan(plan, initial_plan)
    assert not valid
    assert "evidence" in err.lower()

"""Unit tests for RepairSafetyValidator and fingerprinting."""

from codegraph.change.models import ChangeOperation, ChangeOperationType, ChangePlan, ChangeRiskLevel
from codegraph.repair.models import FailureCategory, FailureDiagnosis, RepairPlan
from codegraph.repair.safety import RepairSafetyValidator
from codegraph.repair.stopping import FingerprintManager


def test_repair_safety_validator_rejects_forbidden_keyword() -> None:
    diagnosis = FailureDiagnosis(
        failure_id="F1",
        category=FailureCategory.SYNTAX_ERROR,
        root_cause_hypothesis="Error",
        confidence="HIGH",
        evidence_ids=("E1",),
    )
    op = ChangeOperation(
        file="services.py",
        operation_type=ChangeOperationType.MODIFY_FUNCTION,
        target="UserService",
        description="Run git commit to save changes",
        rationale="Unsafe rationale",
        evidence_ids=("E1",),
        new_code="import os; os.system('git commit')",
    )
    plan = RepairPlan(
        objective="Unsafe repair",
        diagnosis=diagnosis,
        modifications=(op,),
        affected_entities=("UserService",),
        affected_files=("services.py",),
        validation_strategy="None",
        expected_fix="None",
    )

    safe, err = RepairSafetyValidator.validate_plan_safety(plan)
    assert not safe
    assert "security violation" in err.lower() or "forbidden keyword" in err.lower()


def test_fingerprint_manager_deterministic() -> None:
    fp1 = FingerprintManager.compute_failure_fingerprint([])
    assert fp1 == "EMPTY_FAILURES"

    diag = FailureDiagnosis(
        failure_id="F1",
        category=FailureCategory.SYNTAX_ERROR,
        root_cause_hypothesis="IndentationError",
        confidence="HIGH",
        affected_entities=("UserService",),
    )
    dfp = FingerprintManager.compute_diagnosis_fingerprint(diag)
    assert len(dfp) == 16

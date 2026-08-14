"""Unit tests for Phase 8 Change Planner & Risk Analysis."""

from codegraph.change.planner import DeterministicChangePlanner, ChangePlanValidator
from codegraph.change.models import ChangeRequest, ChangeRiskLevel, ChangePlan, ChangeOperation, ChangeOperationType
from codegraph.change.impact import ChangeRiskAnalyzer


def test_deterministic_change_planner() -> None:
    """Verify deterministic change planner generates evidence-grounded plan."""
    planner = DeterministicChangePlanner()
    req = ChangeRequest(description="Fix UserService authorization mismatch", repository_id="repo")
    plan = planner.create_plan(req)

    assert plan.is_valid
    assert plan.objective.startswith("Resolve issue:")
    assert len(plan.modifications) == 1
    assert plan.modifications[0].file == "services.py"
    assert plan.risks == ChangeRiskLevel.LOW


def test_change_plan_validator_rejects_unsupported_ops() -> None:
    """Verify plan validator rejects invalid or ungrounded plans."""
    op = ChangeOperation(
        file="../outside.py",
        operation_type=ChangeOperationType.MODIFY_FUNCTION,
        target="foo",
        description="invalid path",
        rationale="test",
    )
    plan = ChangePlan(
        objective="test",
        root_cause="test",
        affected_entities=("foo",),
        affected_files=("../outside.py",),
        modifications=(op,),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="test",
    )

    valid, reason = ChangePlanValidator.validate_plan(plan)
    assert not valid
    assert "Invalid file path" in reason


def test_change_risk_analyzer_blocked_keywords() -> None:
    """Verify risk analyzer flags database/schema changes as BLOCKED."""
    op = ChangeOperation(
        file="schema.sql",
        operation_type=ChangeOperationType.MODIFY_FUNCTION,
        target="table",
        description="Perform database migration and drop table",
        rationale="test",
    )
    plan = ChangePlan(
        objective="test",
        root_cause="Database schema update",
        affected_entities=("db",),
        affected_files=("schema.sql",),
        modifications=(op,),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="test",
    )

    risk = ChangeRiskAnalyzer.calculate_risk(plan)
    assert risk == ChangeRiskLevel.BLOCKED

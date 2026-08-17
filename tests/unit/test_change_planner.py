"""Unit tests for Phase 8 Change Planner & Risk Analysis."""

import pytest
from codegraph.change.planner import DeterministicChangePlanner, ChangePlanValidator
from codegraph.change.models import ChangeRequest, ChangeRiskLevel, ChangePlan, ChangeOperation, ChangeOperationType
from codegraph.change.impact import ChangeRiskAnalyzer


def test_deterministic_change_planner() -> None:
    """Deterministic planner grounds its plan in the actual repository sources."""
    planner = DeterministicChangePlanner()
    sources = {
        "services.py": (
            "class UserService:\n"
            "    def authenticate(self, user_id):\n"
            "        return True\n"
        ),
    }
    req = ChangeRequest(description="Fix UserService.authenticate authorization mismatch", repository_id="repo")
    plan = planner.create_plan(req, source_code_map=sources)

    assert plan.is_valid
    assert plan.objective.startswith("Resolve issue:")
    assert len(plan.modifications) == 1
    assert plan.modifications[0].file == "services.py"
    assert plan.modifications[0].target.endswith("UserService.authenticate")
    # The patch is derived from the real file, so the original class is preserved.
    assert "class UserService" in (plan.modifications[0].new_code or "")
    assert plan.risks == ChangeRiskLevel.LOW


def test_deterministic_change_planner_abstains_without_real_target() -> None:
    """With no graph and no matching source entity, the planner must abstain."""
    planner = DeterministicChangePlanner()
    req = ChangeRequest(description="Fix authorization mismatch", repository_id="repo")
    plan = planner.create_plan(req)

    assert not plan.is_valid
    assert "does not reference any component" in plan.rejection_reason


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


def test_change_planner_blocks_database_migration_bypass() -> None:
    """Regression test: raw request with blocked keywords must result in BLOCKED risk and is_valid=False."""
    planner = DeterministicChangePlanner()
    sources = {
        "services.py": (
            "class UserService:\n"
            "    def authenticate(self, user_id):\n"
            "        return True\n"
        ),
    }
    req = ChangeRequest(
        description="Perform database migration DROP TABLE on UserService",
        repository_id="repo",
    )
    plan = planner.create_plan(req, source_code_map=sources)

    assert plan.risks == ChangeRiskLevel.BLOCKED
    assert not plan.is_valid
    assert "BLOCKED" in (plan.rejection_reason or "")


@pytest.mark.parametrize(
    "phrase,term",
    [
        ("apply schema migration script for UserService", "migration"),
        ("update the user schema definition in UserService", "schema"),
        ("connect to external database from UserService", "database"),
        ("add a new column to the users table in UserService", "table"),
        ("execute raw sql query inside UserService", "sql"),
    ],
)
def test_blocklist_individual_terms_in_requests(phrase: str, term: str) -> None:
    """Verify each blocked keyword in a natural user request triggers BLOCKED risk level."""
    planner = DeterministicChangePlanner()
    sources = {
        "services.py": (
            "class UserService:\n"
            "    def authenticate(self, user_id):\n"
            "        return True\n"
        ),
    }
    req = ChangeRequest(description=phrase, repository_id="repo")
    plan = planner.create_plan(req, source_code_map=sources)

    assert plan.risks == ChangeRiskLevel.BLOCKED, f"Expected {phrase} containing term '{term}' to be BLOCKED"
    assert not plan.is_valid
    assert "BLOCKED" in (plan.rejection_reason or "")


def test_blocklist_affected_files_and_entities() -> None:
    """Verify plans referencing files or entities with blocked keywords are BLOCKED."""
    plan_with_file = ChangePlan(
        objective="Refactor service",
        root_cause="Clean code",
        affected_entities=("UserService",),
        affected_files=("db_migration.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="test",
    )
    assert ChangeRiskAnalyzer.calculate_risk(plan_with_file) == ChangeRiskLevel.BLOCKED

    plan_with_entity = ChangePlan(
        objective="Refactor service",
        root_cause="Clean code",
        affected_entities=("UserTable",),
        affected_files=("services.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="test",
    )
    assert ChangeRiskAnalyzer.calculate_risk(plan_with_entity) == ChangeRiskLevel.BLOCKED


def test_calculate_risk_objective_fallback() -> None:
    """Verify calculate_risk checks plan.objective when request_text is not provided."""
    plan = ChangePlan(
        objective="Resolve issue: update database schema for UserService",
        root_cause="Standard update",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="test",
    )
    assert ChangeRiskAnalyzer.calculate_risk(plan) == ChangeRiskLevel.BLOCKED



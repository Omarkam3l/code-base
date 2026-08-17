"""Unit tests for Phase 8 Safety & Security Validation."""

import pytest
from codegraph.change.safety import SafetyValidator


def test_path_traversal_rejection() -> None:
    """Verify path traversal sequences are rejected."""
    valid, reason = SafetyValidator.validate_path("../outside.py")
    assert not valid
    assert "traversal" in reason.lower()

    valid2, reason2 = SafetyValidator.validate_path("sub/../../escaped.py")
    assert not valid2


def test_absolute_path_rejection() -> None:
    """Verify absolute paths are rejected."""
    valid, reason = SafetyValidator.validate_path("/etc/passwd")
    assert not valid
    assert "absolute" in reason.lower()

    valid2, reason2 = SafetyValidator.validate_path("C:\\Windows\\System32\\cmd.exe")
    assert not valid2


def test_forbidden_operations_rejection() -> None:
    """Verify forbidden operations are rejected."""
    valid, reason = SafetyValidator.validate_operation_type("DELETE_FILE")
    assert not valid
    assert "forbidden" in reason.lower()

    valid2, reason2 = SafetyValidator.validate_operation_type("DATABASE_MIGRATIONS")
    assert not valid2


def test_supported_operations_accepted() -> None:
    """Verify supported operations pass validation."""
    valid, reason = SafetyValidator.validate_operation_type("MODIFY_FUNCTION")
    assert valid
    assert reason is None


def test_patch_bounds_clamping() -> None:
    """Verify patch bounds enforcement."""
    valid, reason = SafetyValidator.validate_patch_bounds(file_count=5, lines_changed=100)
    assert valid

    valid2, reason2 = SafetyValidator.validate_patch_bounds(file_count=15, lines_changed=100)
    assert not valid2
    assert "file count" in reason2.lower()

    valid3, reason3 = SafetyValidator.validate_patch_bounds(file_count=5, lines_changed=500)
    assert not valid3
    assert "changed lines" in reason3.lower()


def test_dangerous_sql_operations_rejection() -> None:
    """Verify dangerous SQL DDL/DML operations are blocked by pattern matching."""
    from codegraph.change.models import ChangeRequest, ChangeRiskLevel
    from codegraph.change.planner import DeterministicChangePlanner

    planner = DeterministicChangePlanner()
    sources = {"services.py": "class UserService:\n    def add_user(self, name):\n        pass\n"}

    dangerous_reqs = [
        "Perform database migration DROP TABLE on UserService",
        "TRUNCATE users in UserService",
        "DELETE FROM users in UserService",
        "ALTER TABLE users ADD COLUMN role TEXT",
    ]

    for req_text in dangerous_reqs:
        plan = planner.create_plan(ChangeRequest(description=req_text, repository_id="repo:test"), source_code_map=sources)
        assert not plan.is_valid, f"Expected {req_text} to be invalid"
        assert plan.risks == ChangeRiskLevel.BLOCKED
        assert "BLOCKED" in (plan.rejection_reason or "")


def test_legitimate_delete_code_requests_accepted() -> None:
    """Verify legitimate code removal/delete requests are NOT blocked as dangerous DB operations."""
    from codegraph.change.models import ChangeRequest
    from codegraph.change.planner import DeterministicChangePlanner

    planner = DeterministicChangePlanner()
    sources = {"services.py": "class UserService:\n    def add_user(self, name):\n        pass\n"}

    req = ChangeRequest(description="delete add_user method in UserService", repository_id="repo:test")
    plan = planner.create_plan(req, source_code_map=sources)
    assert plan.is_valid, f"Expected legitimate code delete request to be valid, got rejection: {plan.rejection_reason}"


def test_push_authorization_safety() -> None:
    """Verify PushController blocks push execution unless explicitly authorized."""
    from codegraph.git.safety import PushController

    pc = PushController(push_authorized=False)
    assert not pc.is_authorized()
    pushed, reason = pc.push("/tmp/fake_repo", "main")
    assert not pushed
    assert "AUTHORIZATION" in (reason or "")

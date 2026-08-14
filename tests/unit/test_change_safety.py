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

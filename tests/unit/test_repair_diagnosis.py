"""Unit tests for FailureDiagnoser and FakeFailureDiagnoser."""

from codegraph.repair.diagnosis import FailureDiagnoser, FakeFailureDiagnoser
from codegraph.repair.models import FailureCategory, FailureRecord


def test_fake_failure_diagnoser() -> None:
    diagnoser = FakeFailureDiagnoser()
    fail = FailureRecord(
        test_name="test_user_auth",
        test_file="tests/test_services.py",
        error_type="AssertionError",
        error_message="Expected status authenticated",
        traceback="AssertionError",
    )
    diag = diagnoser.diagnose_failure([fail])

    assert diag.category == FailureCategory.ASSERTION_FAILURE
    assert diag.confidence == "HIGH"
    assert "UserService" in diag.affected_entities


def test_failure_diagnoser_empty_failures() -> None:
    diagnoser = FailureDiagnoser()
    diag = diagnoser.diagnose_failure([])

    assert diag.category == FailureCategory.UNKNOWN
    assert diag.confidence == "LOW"

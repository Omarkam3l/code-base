"""Unit tests for FailureParser and failure classification."""

from codegraph.change.models import TestExecutionResult, ValidationResult
from codegraph.repair.failure import FailureParser
from codegraph.repair.models import FailureCategory, FailureRecord


def test_failure_parser_parse_test_result() -> None:
    test_res = TestExecutionResult(
        tests_run=5,
        tests_passed=4,
        tests_failed=1,
        test_failures=("FAILED tests/test_services.py::test_auth - AssertionError: Expected 200 got 401",),
    )
    records = FailureParser.parse_test_result(test_res)
    assert len(records) == 1
    rec = records[0]
    assert rec.test_file == "tests/test_services.py"
    assert rec.test_name == "test_auth"
    assert rec.error_type == "AssertionError"
    assert "Expected 200 got 401" in rec.error_message


def test_failure_parser_parse_validation_result() -> None:
    val_res = ValidationResult(
        syntax_valid=False,
        structural_valid=False,
        tests_passed=False,
        failures=("IndentationError: unexpected indent at line 14",),
    )
    records = FailureParser.parse_validation_result(val_res)
    assert len(records) == 1
    assert records[0].error_type == FailureCategory.SYNTAX_ERROR.value


def test_failure_parser_classify_failure() -> None:
    rec1 = FailureRecord(
        test_name="t1",
        test_file="f1.py",
        error_type="SyntaxError",
        error_message="invalid syntax",
        traceback="SyntaxError: invalid syntax",
    )
    assert FailureParser.classify_failure(rec1) == FailureCategory.SYNTAX_ERROR

    rec2 = FailureRecord(
        test_name="t2",
        test_file="f2.py",
        error_type="ModuleNotFoundError",
        error_message="No module named 'typing'",
        traceback="ModuleNotFoundError: No module named 'typing'",
    )
    assert FailureParser.classify_failure(rec2) == FailureCategory.IMPORT_ERROR

    rec3 = FailureRecord(
        test_name="t3",
        test_file="f3.py",
        error_type="AttributeError",
        error_message="'UserService' has no attribute 'authenticate'",
        traceback="AttributeError: 'UserService' has no attribute 'authenticate'",
    )
    assert FailureParser.classify_failure(rec3) == FailureCategory.MISSING_SYMBOL

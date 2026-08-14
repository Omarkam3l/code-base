"""Deterministic failure parser and classification module for Phase 9."""

import re
from typing import Sequence
from codegraph.change.models import TestExecutionResult, ValidationResult
from codegraph.repair.models import FailureCategory, FailureRecord


class FailureParser:
    """Parses pytest execution output, exit codes, and validation failures into structured FailureRecords."""

    @staticmethod
    def parse_test_result(test_result: TestExecutionResult | None) -> tuple[FailureRecord, ...]:
        """Convert TestExecutionResult failure strings into FailureRecords."""
        if not test_result or not test_result.test_failures:
            return ()

        records: list[FailureRecord] = []
        for fail_str in test_result.test_failures:
            record = FailureParser.parse_failure_string(fail_str)
            records.append(record)

        return tuple(records)

    @staticmethod
    def parse_validation_result(validation_res: ValidationResult | None) -> tuple[FailureRecord, ...]:
        """Convert ValidationResult failures into FailureRecords."""
        if not validation_res or not validation_res.failures:
            return ()

        records: list[FailureRecord] = []
        for fail_str in validation_res.failures:
            cat = FailureParser.classify_error_text(fail_str)
            record = FailureRecord(
                test_name="validation_check",
                test_file="validation",
                error_type=cat.value,
                error_message=fail_str,
                traceback=fail_str,
            )
            records.append(record)

        return tuple(records)

    @staticmethod
    def parse_failure_string(fail_str: str) -> FailureRecord:
        """Parse raw failure string using deterministic regex patterns."""
        # Pattern e.g. "FAILED test_file.py::test_func - ErrorType: error message"
        pattern = r"(?:FAILED\s+)?([^\s:]+(?:\.py)?)::([^\s\-]+)\s*-\s*([A-Za-z0-9_]+):\s*(.*)"
        match = re.search(pattern, fail_str)

        if match:
            test_file, test_name, error_type, error_msg = match.groups()
            return FailureRecord(
                test_name=test_name.strip(),
                test_file=test_file.strip(),
                error_type=error_type.strip(),
                error_message=error_msg.strip(),
                traceback=fail_str,
            )

        # Fallback parsing
        parts = fail_str.split(":", 1)
        if len(parts) == 2:
            return FailureRecord(
                test_name="test_execution",
                test_file="test",
                error_type=parts[0].strip(),
                error_message=parts[1].strip(),
                traceback=fail_str,
            )

        return FailureRecord(
            test_name="test_execution",
            test_file="test",
            error_type="UNKNOWN",
            error_message=fail_str,
            traceback=fail_str,
        )

    @staticmethod
    def classify_failure(record: FailureRecord) -> FailureCategory:
        """Deterministically classify a FailureRecord into a FailureCategory."""
        text = f"{record.error_type} {record.error_message} {record.traceback}".lower()

        if "syntaxerror" in text or "indentationerror" in text or "invalid syntax" in text:
            return FailureCategory.SYNTAX_ERROR
        if "importerror" in text or "modulenotfounderror" in text or "no module named" in text:
            return FailureCategory.IMPORT_ERROR
        if "typeerror" in text:
            return FailureCategory.TYPE_ERROR
        if "assertionerror" in text or "assert" in text:
            return FailureCategory.ASSERTION_FAILURE
        if "timeout" in text or "timed out" in text:
            return FailureCategory.TEST_TIMEOUT
        if "attributeerror" in text or "nameerror" in text or "has no attribute" in text or "is not defined" in text:
            return FailureCategory.MISSING_SYMBOL
        if "patch application" in text or "patch failed" in text or "patch file" in text:
            return FailureCategory.PATCH_APPLICATION_FAILURE
        if "regression" in text or "baseline" in text:
            return FailureCategory.REGRESSION
        if "environment" in text or "no pytest" in text:
            return FailureCategory.ENVIRONMENT_FAILURE
        if any(err in text for err in ["keyerror", "valueerror", "indexerror", "runtimeerror"]):
            return FailureCategory.RUNTIME_ERROR

        return FailureCategory.UNKNOWN

    @staticmethod
    def classify_error_text(error_text: str) -> FailureCategory:
        """Utility wrapper to classify raw error text string."""
        rec = FailureRecord(
            test_name="check",
            test_file="check",
            error_type="check",
            error_message=error_text,
            traceback=error_text,
        )
        return FailureParser.classify_failure(rec)

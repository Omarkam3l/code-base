"""Domain models for Phase 9 Controlled Iterative Patch Repair."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from codegraph.change.models import (
    ChangeOperation,
    ChangePlan,
    ChangeRequest,
    Patch,
    TestExecutionResult,
)


class FailureCategory(str, Enum):
    """Categorized root causes of test and validation failures."""

    SYNTAX_ERROR = "SYNTAX_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TEST_TIMEOUT = "TEST_TIMEOUT"
    MISSING_SYMBOL = "MISSING_SYMBOL"
    REGRESSION = "REGRESSION"
    PATCH_APPLICATION_FAILURE = "PATCH_APPLICATION_FAILURE"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FailureRecord:
    """Detailed record of an individual test or validation failure."""

    test_name: str
    test_file: str
    error_type: str
    error_message: str
    traceback: str
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0


@dataclass(frozen=True)
class FailureDiagnosis:
    """Structured diagnostic hypothesis formed from failure records and evidence."""

    failure_id: str
    category: FailureCategory
    root_cause_hypothesis: str
    confidence: str  # HIGH, MEDIUM, LOW
    evidence_ids: tuple[str, ...] = ()
    affected_entities: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepairPlan:
    """Structured plan outlining modifications required to resolve diagnosed failure."""

    objective: str
    diagnosis: FailureDiagnosis
    modifications: tuple[ChangeOperation, ...]
    affected_entities: tuple[str, ...]
    affected_files: tuple[str, ...]
    validation_strategy: str
    expected_fix: str
    is_valid: bool = True
    rejection_reason: str | None = None
    scope_justification: str | None = None


@dataclass(frozen=True)
class RepairIteration:
    """Record of a single repair attempt iteration."""

    iteration_number: int
    patch: Patch | None
    diagnosis: FailureDiagnosis | None
    repair_plan: RepairPlan | None
    test_result: TestExecutionResult | None
    status: str  # SUCCESS, FAILED, VALIDATION_FAILED, REJECTED
    evidence: tuple[str, ...] = ()
    execution_time_ms: float = 0.0


@dataclass(frozen=True)
class RepairRequest:
    """Container for initiating a repair pipeline for a failed change request or patch."""

    change_request: ChangeRequest
    initial_change_plan: ChangePlan
    initial_patch: Patch | None
    initial_test_result: TestExecutionResult | None = None
    workspace: str | None = None


@dataclass(frozen=True)
class RepairResult:
    """Final outcome of the iterative patch repair process."""

    status: str  # SUCCESS, FAILURE, ABSTAIN
    iterations: tuple[RepairIteration, ...]
    final_patch: Patch | None
    final_test_result: TestExecutionResult | None
    failure_history: tuple[FailureRecord, ...]
    stopping_reason: str
    metrics: Any = None
    execution_time_ms: float = 0.0


@dataclass(frozen=True)
class RepairTrace:
    """Observability trace record for a single iteration step."""

    iteration_number: int
    timestamp: str
    patch_fingerprint: str
    failure_fingerprint: str
    diagnosis: str
    evidence_ids: tuple[str, ...]
    tool_calls: int
    test_result: str
    scope: tuple[str, ...]
    elapsed_time_ms: float
    stopping_reason: str

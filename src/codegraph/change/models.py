"""Domain models for Phase 8 Code Change Planning & Patch Generation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence
from codegraph.agent.models import InvestigationAnswer


class ChangeOperationType(str, Enum):
    """Supported change operations in Phase 8."""

    MODIFY_FUNCTION = "MODIFY_FUNCTION"
    MODIFY_METHOD = "MODIFY_METHOD"
    MODIFY_IMPORT = "MODIFY_IMPORT"
    ADD_FUNCTION = "ADD_FUNCTION"
    ADD_METHOD = "ADD_METHOD"
    ADD_TEST = "ADD_TEST"


class ChangeRiskLevel(str, Enum):
    """Risk levels for proposed change plans."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


FORBIDDEN_OPERATIONS = {
    "DELETE_FILE",
    "RENAME_FILE",
    "MOVE_FILE",
    "BINARY_FILE_MODIFICATION",
    "DATABASE_MIGRATIONS",
    "INFRASTRUCTURE_CHANGES",
}


@dataclass(frozen=True)
class ChangeRequest:
    """Initial request for code change planning."""

    description: str
    repository_id: str
    investigation_context: InvestigationAnswer | None = None


@dataclass(frozen=True)
class ChangeOperation:
    """Individual planned code modification operation."""

    file: str
    operation_type: ChangeOperationType
    target: str
    description: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    new_code: str = ""


@dataclass(frozen=True)
class ChangePlan:
    """Structured plan for code change."""

    objective: str
    root_cause: str
    affected_entities: tuple[str, ...]
    affected_files: tuple[str, ...]
    modifications: tuple[ChangeOperation, ...]
    risks: ChangeRiskLevel
    validation_strategy: str
    evidence_references: tuple[str, ...] = ()
    is_valid: bool = True
    rejection_reason: str | None = None


@dataclass(frozen=True)
class PatchFileChange:
    """Individual file change in unified diff patch."""

    file_path: str
    operation_type: ChangeOperationType
    old_content: str
    new_content: str
    diff_snippet: str


@dataclass(frozen=True)
class Patch:
    """Generated patch containing unified diffs."""

    files: tuple[str, ...]
    unified_diff: str
    file_changes: tuple[PatchFileChange, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    lines_added: int = 0
    lines_removed: int = 0


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for patch and AST structure."""

    syntax_valid: bool
    structural_valid: bool
    tests_passed: bool
    failures: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TestExecutionResult:
    """Pytest execution result inside isolated workspace."""

    tests_run: int
    tests_passed: int
    tests_failed: int
    test_failures: tuple[str, ...] = ()
    execution_time_ms: float = 0.0
    baseline_failed: bool = False
    new_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeResult:
    """Final outcome of change planning, patch generation, and validation."""

    plan: ChangePlan
    patch: Patch | None
    validation: ValidationResult
    test_results: TestExecutionResult | None
    status: str  # VALIDATED, REJECTED, TEST_FAILED, FAILED
    explanation: str
    execution_time_ms: float = 0.0

"""Domain models for Phase 10 Git & Pull Request Engineering Workflow."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GitRepository:
    """Immutable model representing a Git repository's status and current HEAD state."""

    root: str
    repository_id: str
    current_branch: str
    remote: str = "origin"
    head_commit: str = ""


@dataclass(frozen=True)
class GitStatus:
    """Immutable model representing the status of working tree files."""

    branch: str
    clean: bool
    modified_files: tuple[str, ...] = ()
    untracked_files: tuple[str, ...] = ()
    staged_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitDiff:
    """Immutable representation of a Git diff changeset."""

    files: tuple[str, ...]
    additions: int
    deletions: int
    unified_diff: str


@dataclass(frozen=True)
class BranchPlan:
    """Plan for creating a safe, isolated Git feature branch."""

    branch_name: str
    base_branch: str
    purpose: str


@dataclass(frozen=True)
class CommitPlan:
    """Plan for forming a conventional, evidence-grounded commit."""

    message: str
    body: str
    files: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class CommitResult:
    """Outcome of creating a local Git commit."""

    commit_hash: str
    branch: str
    message: str
    parent_hash: str = ""
    author: str = ""
    timestamp: str = ""
    additions: int = 0
    deletions: int = 0


@dataclass(frozen=True)
class PullRequestPlan:
    """Structured proposal for a Pull Request containing evidence provenance."""

    title: str
    summary: str
    problem: str
    root_cause: str
    changes: tuple[str, ...]
    tests: str
    risks: str
    evidence: tuple[str, ...]
    branch: str
    base_branch: str


@dataclass(frozen=True)
class GitWorkflowResult:
    """Final outcome of the Phase 10 Git engineering workflow."""

    status: str  # READY, BLOCKED, VALIDATION_FAILED, BRANCH_FAILED, COMMIT_FAILED, PUSH_REQUIRES_AUTHORIZATION, PR_READY, CONCURRENT_CHANGE
    branch: str
    diff: GitDiff | None
    commit: CommitResult | None
    pull_request: PullRequestPlan | None
    validation: Any = None
    errors: tuple[str, ...] = ()
    execution_time_ms: float = 0.0

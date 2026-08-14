"""Domain models for Phase 11 Real GitHub Integration, CI Monitoring & PR Review Loop."""

from dataclasses import dataclass, field
from typing import Any
from codegraph.git.models import GitWorkflowResult
from codegraph.repair.models import RepairResult


@dataclass(frozen=True)
class GitHubEvent:
    """Raw incoming GitHub event or webhook payload."""

    event_id: str
    event_type: str  # pr_opened, pr_synchronize, ci_completed, review_comment
    repository: str
    pr_number: int
    branch: str
    sender: str
    payload: dict[str, Any]
    timestamp: str = ""


@dataclass(frozen=True)
class NormalizedEvent:
    """Normalized event structure consumable by CodeGraph Agent."""

    event_id: str
    event_type: str
    repository: str
    pr_number: int
    branch: str
    query_or_instruction: str
    context_metadata: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PRMetadata:
    """Metadata representing a GitHub Pull Request."""

    pr_number: int
    title: str
    body: str
    author: str
    state: str  # open, closed, merged
    head_sha: str
    head_branch: str
    base_branch: str
    html_url: str = ""
    labels: tuple[str, ...] = ()
    draft: bool = False


@dataclass(frozen=True)
class CIRunStatus:
    """Representation of GitHub Actions CI check run state and logs."""

    run_id: str
    workflow_name: str
    status: str  # queued, in_progress, completed
    conclusion: str  # success, failure, cancelled, timed_out
    failed_jobs: tuple[str, ...] = ()
    log_url: str = ""
    head_sha: str = ""
    failure_details: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewComment:
    """Representation of an inline GitHub Pull Request review comment."""

    comment_id: str
    path: str
    line: int
    author: str
    body: str
    diff_hunk: str = ""
    created_at: str = ""
    in_reply_to_id: str | None = None


@dataclass(frozen=True)
class GitHubWorkflowResult:
    """Outcome of the Phase 11 GitHub integration workflow."""

    status: str  # SUCCESS, REPAIR_PROPOSED, CI_FAILED, REVIEW_PROCESSED, BLOCKED, ABSTAIN
    pr_metadata: PRMetadata | None
    ci_status: CIRunStatus | None
    reviews_processed: tuple[ReviewComment, ...] = ()
    git_result: GitWorkflowResult | None = None
    repair_result: RepairResult | None = None
    errors: tuple[str, ...] = ()
    execution_time_ms: float = 0.0

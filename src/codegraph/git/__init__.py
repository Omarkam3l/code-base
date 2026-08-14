"""Phase 10 Git & Pull Request Engineering Workflow package exports."""

from codegraph.git.models import (
    BranchPlan,
    CommitPlan,
    CommitResult,
    GitDiff,
    GitRepository,
    GitStatus,
    GitWorkflowResult,
    PullRequestPlan,
)
from codegraph.git.repository import FakeGitRepository, GitRepositoryInspector, WorktreeManager
from codegraph.git.branch import BranchManager, FakeBranchManager
from codegraph.git.diff import GitDiffInspector
from codegraph.git.validation import ConcurrentChangeDetector, SecretDetector
from codegraph.git.commit import CommitPlanner, CommitValidator, Committer, FakeCommitter
from codegraph.git.pr import FakePullRequestProvider, PRGenerator, PullRequestProvider
from codegraph.git.safety import GitSafetyValidator, PushController
from codegraph.git.metrics import GitEvaluationMetrics, calculate_git_metrics
from codegraph.git.pipeline import GitWorkflowPipeline

__all__ = [
    "GitRepository",
    "GitStatus",
    "GitDiff",
    "BranchPlan",
    "CommitPlan",
    "CommitResult",
    "PullRequestPlan",
    "GitWorkflowResult",
    "GitRepositoryInspector",
    "WorktreeManager",
    "FakeGitRepository",
    "BranchManager",
    "FakeBranchManager",
    "GitDiffInspector",
    "SecretDetector",
    "ConcurrentChangeDetector",
    "CommitPlanner",
    "CommitValidator",
    "Committer",
    "FakeCommitter",
    "PRGenerator",
    "PullRequestProvider",
    "FakePullRequestProvider",
    "PushController",
    "GitSafetyValidator",
    "GitEvaluationMetrics",
    "calculate_git_metrics",
    "GitWorkflowPipeline",
]

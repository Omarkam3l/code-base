"""Phase 11 Real GitHub Integration, CI Monitoring & PR Review Loop package exports."""

from codegraph.github.models import (
    CIRunStatus,
    GitHubEvent,
    GitHubWorkflowResult,
    NormalizedEvent,
    PRMetadata,
    ReviewComment,
)
from codegraph.github.client import FakeGitHubClient, GitHubClient
from codegraph.github.pr_manager import PRManager
from codegraph.github.ci_monitor import CIMonitor
from codegraph.github.review_manager import ReviewManager
from codegraph.github.event_normalizer import EventNormalizer
from codegraph.github.safety import GitHubSafetyController
from codegraph.github.metrics import GitHubEvaluationMetrics, calculate_github_metrics
from codegraph.github.pipeline import GitHubWorkflowPipeline

__all__ = [
    "GitHubEvent",
    "NormalizedEvent",
    "PRMetadata",
    "CIRunStatus",
    "ReviewComment",
    "GitHubWorkflowResult",
    "GitHubClient",
    "FakeGitHubClient",
    "PRManager",
    "CIMonitor",
    "ReviewManager",
    "EventNormalizer",
    "GitHubSafetyController",
    "GitHubEvaluationMetrics",
    "calculate_github_metrics",
    "GitHubWorkflowPipeline",
]

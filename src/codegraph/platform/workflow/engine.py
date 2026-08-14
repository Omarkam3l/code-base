"""Human Approval Workflow State Engine enforcing approval gates."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any
from codegraph.git.safety import PushController
from codegraph.github.safety import GitHubSafetyController


class WorkflowState(str, Enum):
    """Explicit lifecycle states for CodeGraph Platform changes."""

    ANALYZE = "ANALYZE"
    INVESTIGATE = "INVESTIGATE"
    PLAN = "PLAN"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    PATCH = "PATCH"
    TEST = "TEST"
    AWAITING_GIT_APPROVAL = "AWAITING_GIT_APPROVAL"
    COMMIT = "COMMIT"
    PR = "PR"
    CI = "CI"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowContext:
    """Context holding workflow state, approval records, and metadata."""

    workflow_id: str
    repository_id: str
    current_state: WorkflowState = WorkflowState.ANALYZE
    plan_approved: bool = False
    git_commit_approved: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)


class ApprovalWorkflowEngine:
    """State machine managing platform workflows and enforcing approval gates."""

    ALLOWED_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
        WorkflowState.ANALYZE: {WorkflowState.INVESTIGATE, WorkflowState.FAILED},
        WorkflowState.INVESTIGATE: {WorkflowState.PLAN, WorkflowState.FAILED},
        WorkflowState.PLAN: {WorkflowState.AWAITING_APPROVAL, WorkflowState.FAILED},
        WorkflowState.AWAITING_APPROVAL: {WorkflowState.PATCH, WorkflowState.FAILED},
        WorkflowState.PATCH: {WorkflowState.TEST, WorkflowState.FAILED},
        WorkflowState.TEST: {WorkflowState.AWAITING_GIT_APPROVAL, WorkflowState.FAILED},
        WorkflowState.AWAITING_GIT_APPROVAL: {WorkflowState.COMMIT, WorkflowState.FAILED},
        WorkflowState.COMMIT: {WorkflowState.PR, WorkflowState.FAILED},
        WorkflowState.PR: {WorkflowState.CI, WorkflowState.FAILED},
        WorkflowState.CI: {WorkflowState.REVIEW, WorkflowState.COMPLETED, WorkflowState.FAILED},
        WorkflowState.REVIEW: {WorkflowState.COMPLETED, WorkflowState.FAILED},
        WorkflowState.COMPLETED: set(),
        WorkflowState.FAILED: set(),
    }

    def __init__(self) -> None:
        self.push_controller = PushController(push_authorized=False)
        self.github_safety = GitHubSafetyController()

    def transition(self, context: WorkflowContext, target_state: WorkflowState) -> WorkflowContext:
        """Attempt state transition enforcing human approval gates."""
        current = context.current_state
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())

        if target_state not in allowed:
            raise ValueError(f"Invalid workflow transition: {current.value} -> {target_state.value}")

        # Enforce Approval Gate 1: PLAN -> PATCH requires explicit approval
        if current == WorkflowState.AWAITING_APPROVAL and target_state == WorkflowState.PATCH:
            if not context.plan_approved:
                raise PermissionError("Approval gate blocked: Change plan has not received explicit human approval.")

        # Enforce Approval Gate 2: TEST -> COMMIT requires explicit approval
        if current == WorkflowState.AWAITING_GIT_APPROVAL and target_state == WorkflowState.COMMIT:
            if not context.git_commit_approved:
                raise PermissionError("Approval gate blocked: Git commit has not received explicit human approval.")

        context.history.append({
            "from_state": current.value,
            "to_state": target_state.value,
        })
        context.current_state = target_state
        return context

    def approve_plan(self, context: WorkflowContext) -> WorkflowContext:
        """Grant human approval for change plan execution."""
        context.plan_approved = True
        return context

    def approve_git_commit(self, context: WorkflowContext) -> WorkflowContext:
        """Grant human approval for git commit execution."""
        context.git_commit_approved = True
        return context

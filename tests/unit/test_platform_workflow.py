"""Unit tests for ApprovalWorkflowEngine state machine and approval gates."""

import pytest
from codegraph.platform.workflow.engine import ApprovalWorkflowEngine, WorkflowContext, WorkflowState


def test_workflow_state_transitions_and_approval_gates() -> None:
    engine = ApprovalWorkflowEngine()
    ctx = WorkflowContext(workflow_id="wf_001", repository_id="repository:sample_project")

    # Step 1: ANALYZE -> INVESTIGATE -> PLAN
    ctx = engine.transition(ctx, WorkflowState.INVESTIGATE)
    assert ctx.current_state == WorkflowState.INVESTIGATE

    ctx = engine.transition(ctx, WorkflowState.PLAN)
    assert ctx.current_state == WorkflowState.PLAN

    ctx = engine.transition(ctx, WorkflowState.AWAITING_APPROVAL)
    assert ctx.current_state == WorkflowState.AWAITING_APPROVAL

    # Unapproved PLAN -> PATCH transition must raise PermissionError
    with pytest.raises(PermissionError, match="Approval gate blocked"):
        engine.transition(ctx, WorkflowState.PATCH)

    # Approve plan and transition to PATCH
    ctx = engine.approve_plan(ctx)
    ctx = engine.transition(ctx, WorkflowState.PATCH)
    assert ctx.current_state == WorkflowState.PATCH

    ctx = engine.transition(ctx, WorkflowState.TEST)
    assert ctx.current_state == WorkflowState.TEST

    ctx = engine.transition(ctx, WorkflowState.AWAITING_GIT_APPROVAL)
    assert ctx.current_state == WorkflowState.AWAITING_GIT_APPROVAL

    # Unapproved TEST -> COMMIT transition must raise PermissionError
    with pytest.raises(PermissionError, match="Approval gate blocked"):
        engine.transition(ctx, WorkflowState.COMMIT)

    # Approve commit and transition to COMMIT
    ctx = engine.approve_git_commit(ctx)
    ctx = engine.transition(ctx, WorkflowState.COMMIT)
    assert ctx.current_state == WorkflowState.COMMIT

"""End-to-end GitWorkflowPipeline orchestrating Phase 10 Git & PR Engineering Workflow."""

import time
from pathlib import Path
from typing import Sequence
from codegraph.change.models import ChangePlan, Patch
from codegraph.git.branch import BranchManager, FakeBranchManager
from codegraph.git.commit import CommitPlanner, CommitValidator, Committer, FakeCommitter
from codegraph.git.diff import GitDiffInspector
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
from codegraph.git.pr import FakePullRequestProvider, PRGenerator, PullRequestProvider
from codegraph.git.repository import FakeGitRepository, GitRepositoryInspector, WorktreeManager
from codegraph.git.safety import PushController
from codegraph.git.validation import ConcurrentChangeDetector, SecretDetector
from codegraph.repair.models import RepairResult


class GitWorkflowPipeline:
    """Orchestrates Phase 10 Git Engineering Workflow from verified repair to PR proposal."""

    def __init__(
        self,
        inspector: GitRepositoryInspector | None = None,
        use_deterministic: bool = True,
        push_authorized: bool = False,
        pr_provider: PullRequestProvider | None = None,
    ) -> None:
        self.inspector = inspector
        self.use_deterministic = use_deterministic
        self.push_controller = PushController(push_authorized=push_authorized)
        self.pr_provider = pr_provider or FakePullRequestProvider()

    def process_git_workflow(
        self,
        change_plan: ChangePlan,
        patch: Patch | None,
        repair_result: RepairResult | None,
        source_repo_path: str | Path,
        source_code_map: dict[str, str],
        request_push: bool = False,
        existing_branches: set[str] | None = None,
        baseline_head: str | None = None,
        secret_override_content: str | None = None,
        concurrent_change_triggered: bool = False,
    ) -> GitWorkflowResult:
        """Execute full Git workflow: Inspect -> Worktree -> Branch -> Diff -> Secret Scan -> Commit -> PR Proposal."""
        start_time = time.perf_counter()
        errors: list[str] = []

        # Step 1: Repository Inspection
        inspector = self.inspector or (FakeGitRepository() if self.use_deterministic else GitRepositoryInspector(source_repo_path))
        repo_info = inspector.get_repository_info()
        repo_status = inspector.get_status()

        # Check concurrent repository modification
        if concurrent_change_triggered:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="CONCURRENT_CHANGE",
                branch=repo_info.current_branch,
                diff=None,
                commit=None,
                pull_request=None,
                errors=("CONCURRENT_REPOSITORY_CHANGE: HEAD commit changed unexpectedly during workflow execution.",),
                execution_time_ms=elapsed,
            )

        # Step 2: Convert Patch to GitDiff and Inspect Scope
        git_diff = GitDiffInspector.create_git_diff_from_patch(patch)
        diff_ok, diff_err = GitDiffInspector.inspect_diff(git_diff, change_plan)
        if not diff_ok:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="VALIDATION_FAILED",
                branch=repo_info.current_branch,
                diff=git_diff,
                commit=None,
                pull_request=None,
                errors=(diff_err or "Diff inspection failed.",),
                execution_time_ms=elapsed,
            )

        # Step 3: Local Secret Detection
        scan_content = git_diff.unified_diff
        if secret_override_content:
            scan_content = secret_override_content

        clean_secrets, secret_err = SecretDetector.scan_diff_for_secrets(scan_content)
        if not clean_secrets:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="VALIDATION_FAILED",
                branch=repo_info.current_branch,
                diff=git_diff,
                commit=None,
                pull_request=None,
                errors=(secret_err or "Secret leakage detected in source diff.",),
                execution_time_ms=elapsed,
            )

        # Step 4: Branch Management
        target_entity = change_plan.affected_entities[0] if change_plan.affected_entities else "patch"
        branch_plan = BranchManager.create_branch_plan(
            category="fix",
            short_id=target_entity,
            base_branch=repo_info.current_branch,
            existing_branches=existing_branches,
        )

        valid_b, b_err = BranchManager.validate_branch_name(branch_plan.branch_name)
        if not valid_b:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="BRANCH_FAILED",
                branch=repo_info.current_branch,
                diff=git_diff,
                commit=None,
                pull_request=None,
                errors=(b_err or "Branch name validation failed.",),
                execution_time_ms=elapsed,
            )

        # Step 5: Commit Planning & Validation
        commit_plan = CommitPlanner.plan_commit(change_plan, repair_result, git_diff)
        valid_c, c_err = CommitValidator.validate_commit_plan(commit_plan, git_diff)
        if not valid_c:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="VALIDATION_FAILED",
                branch=branch_plan.branch_name,
                diff=git_diff,
                commit=None,
                pull_request=None,
                errors=(c_err or "Commit validation failed.",),
                execution_time_ms=elapsed,
            )

        # Step 6: Commit Creation inside Isolated Worktree
        if self.use_deterministic:
            committer = FakeCommitter()
            commit_res, commit_err = committer.commit(commit_plan, branch_plan.branch_name)
        else:
            wt_mgr = WorktreeManager(source_repo_path)
            wt_dir, wt_err = wt_mgr.create_worktree(branch_plan.branch_name)
            if wt_err or not wt_dir:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return GitWorkflowResult(
                    status="BRANCH_FAILED",
                    branch=branch_plan.branch_name,
                    diff=git_diff,
                    commit=None,
                    pull_request=None,
                    errors=(f"Worktree creation error: {wt_err}",),
                    execution_time_ms=elapsed,
                )

            committer = Committer(wt_dir)
            commit_res, commit_err = committer.commit(commit_plan, branch_plan.branch_name)
            wt_mgr.remove_worktree(wt_dir)

        if commit_err or not commit_res:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return GitWorkflowResult(
                status="COMMIT_FAILED",
                branch=branch_plan.branch_name,
                diff=git_diff,
                commit=None,
                pull_request=None,
                errors=(commit_err or "Commit creation failed.",),
                execution_time_ms=elapsed,
            )

        # Step 7: Formulate Pull Request Proposal
        pr_plan = PRGenerator.generate_pr_plan(
            change_plan=change_plan,
            branch_plan=branch_plan,
            repair_result=repair_result,
            git_diff=git_diff,
            commit_result=commit_res,
        )

        # Step 8: Push Authorization Check
        if request_push:
            pushed, push_err = self.push_controller.push(source_repo_path, branch_plan.branch_name, repo_info.remote)
            if not pushed:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return GitWorkflowResult(
                    status="PUSH_REQUIRES_AUTHORIZATION" if "AUTHORIZATION" in (push_err or "") else "COMMIT_FAILED",
                    branch=branch_plan.branch_name,
                    diff=git_diff,
                    commit=commit_res,
                    pull_request=pr_plan,
                    errors=(push_err or "Push requires explicit authorization.",),
                    execution_time_ms=elapsed,
                )

        elapsed = (time.perf_counter() - start_time) * 1000.0
        return GitWorkflowResult(
            status="PR_READY",
            branch=branch_plan.branch_name,
            diff=git_diff,
            commit=commit_res,
            pull_request=pr_plan,
            execution_time_ms=elapsed,
        )

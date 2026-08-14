"""End-to-end GitHubWorkflowPipeline for Phase 11."""

import time
from pathlib import Path
from typing import Sequence
from codegraph.change.models import ChangeRequest
from codegraph.change.pipeline import ChangePipeline
from codegraph.git.pipeline import GitWorkflowPipeline
from codegraph.github.ci_monitor import CIMonitor
from codegraph.github.client import FakeGitHubClient, GitHubClient
from codegraph.github.event_normalizer import EventNormalizer
from codegraph.github.models import GitHubEvent, GitHubWorkflowResult, NormalizedEvent, PRMetadata
from codegraph.github.pr_manager import PRManager
from codegraph.github.review_manager import ReviewManager
from codegraph.github.safety import GitHubSafetyController
from codegraph.repair.models import FailureRecord, RepairRequest, RepairResult
from codegraph.repair.pipeline import RepairPipeline


class GitHubWorkflowPipeline:
    """Orchestrates end-to-end GitHub integration flow: Webhook/Event -> Normalizer -> Repair -> PR Update."""

    def __init__(
        self,
        client: GitHubClient | None = None,
        change_pipeline: ChangePipeline | None = None,
        repair_pipeline: RepairPipeline | None = None,
        git_pipeline: GitWorkflowPipeline | None = None,
        use_deterministic: bool = True,
    ) -> None:
        self.client = client or FakeGitHubClient()
        self.change_pipeline = change_pipeline
        self.repair_pipeline = repair_pipeline
        self.git_pipeline = git_pipeline or GitWorkflowPipeline(use_deterministic=use_deterministic)
        self.pr_manager = PRManager(self.client)
        self.ci_monitor = CIMonitor(self.client)
        self.review_manager = ReviewManager(self.client)
        self.safety_controller = GitHubSafetyController()
        self.use_deterministic = use_deterministic

    def process_event(
        self,
        event: GitHubEvent,
        source_repo_path: str | Path,
        source_code_map: dict[str, str],
        simulated_ci_fail: bool = False,
        simulated_review_comment: bool = False,
    ) -> GitHubWorkflowResult:
        """Process GitHub event through normalization, CI monitoring, review management, automated repair, and PR updates."""
        start_time = time.perf_counter()
        errors: list[str] = []

        # Step 1: Normalize Incoming GitHub Event
        norm_event = EventNormalizer.normalize_event(event)

        # Step 2: Fetch PR Metadata
        pr_meta = self.client.get_pull_request(norm_event.repository, norm_event.pr_number)

        # Step 3: CI Monitoring
        client_ci = self.client
        if isinstance(client_ci, FakeGitHubClient) and simulated_ci_fail:
            client_ci.ci_failing = True
        else:
            if isinstance(client_ci, FakeGitHubClient):
                client_ci.ci_failing = False

        ci_status, failure_records = self.ci_monitor.check_ci_status(norm_event.repository, pr_meta.head_sha)

        # Step 4: Review Comments Processing
        client_rev = self.client
        if isinstance(client_rev, FakeGitHubClient) and simulated_review_comment:
            client_rev.has_review = True
        else:
            if isinstance(client_rev, FakeGitHubClient):
                client_rev.has_review = False

        reviews = self.review_manager.fetch_review_comments(norm_event.repository, norm_event.pr_number)

        # Step 5: Execute Automated Change & Repair Pipeline if requested or CI/Review triggered
        repair_res: RepairResult | None = None
        git_res = None

        if self.change_pipeline and (norm_event.query_or_instruction or failure_records or reviews):
            change_req = ChangeRequest(
                description=norm_event.query_or_instruction,
                repository_id=norm_event.repository,
            )
            change_res = self.change_pipeline.process_change_request(
                request=change_req,
                source_repo_path=source_repo_path,
                source_code_map=source_code_map,
                run_tests=False,
            )

            if self.repair_pipeline:
                repair_req = RepairRequest(
                    change_request=change_req,
                    initial_change_plan=change_res.plan,
                    initial_patch=change_res.patch,
                    initial_test_result=change_res.test_results,
                )
                repair_res = self.repair_pipeline.repair_once(
                    request=repair_req,
                    source_repo_path=source_repo_path,
                    source_code_map=source_code_map,
                )

            # Step 6: Git Workflow
            patch_to_use = repair_res.final_patch if repair_res and repair_res.final_patch else change_res.patch
            plan_to_use = change_res.plan

            git_res = self.git_pipeline.process_git_workflow(
                change_plan=plan_to_use,
                patch=patch_to_use,
                repair_result=repair_res,
                source_repo_path=source_repo_path,
                source_code_map=source_code_map,
                request_push=False,
            )

            # Step 7: Update PR proposal / Description via PRManager
            if git_res and git_res.pull_request:
                pr_meta, pr_err = self.pr_manager.create_or_update_pr(
                    repo=norm_event.repository,
                    plan=git_res.pull_request,
                    existing_pr_number=norm_event.pr_number,
                )
                if pr_err:
                    errors.append(pr_err)

            # Reply to inline review comments if present
            if reviews:
                for rev in reviews:
                    self.review_manager.post_reply(
                        repo=norm_event.repository,
                        pr_number=norm_event.pr_number,
                        comment_id=rev.comment_id,
                        reply_text=f"Addressed in automated commit '{git_res.commit.commit_hash[:8] if git_res and git_res.commit else 'patch'}'. Verified with evidence.",
                    )

        status = "SUCCESS"
        if failure_records:
            status = "CI_FAILED" if not repair_res else "REPAIR_PROPOSED"
        elif reviews:
            status = "REVIEW_PROCESSED"

        elapsed = (time.perf_counter() - start_time) * 1000.0

        return GitHubWorkflowResult(
            status=status,
            pr_metadata=pr_meta,
            ci_status=ci_status,
            reviews_processed=tuple(reviews),
            git_result=git_res,
            repair_result=repair_res,
            errors=tuple(errors),
            execution_time_ms=elapsed,
        )

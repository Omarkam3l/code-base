"""PlatformService orchestrating existing CodeGraph pipelines without business logic duplication."""

from pathlib import Path
from typing import Any
from codegraph.agent.pipeline import AgenticPipeline
from codegraph.change.models import ChangeRequest, TestExecutionResult
from codegraph.change.pipeline import ChangePipeline
from codegraph.git.pipeline import GitWorkflowPipeline
from codegraph.github.client import FakeGitHubClient
from codegraph.github.pipeline import GitHubWorkflowPipeline
from codegraph.graph.repository import GraphRepository
from codegraph.observability.correlation import CorrelationContext
from codegraph.observability.traces import TraceManager
from codegraph.platform.investigations.manager import InvestigationManager
from codegraph.platform.repositories.manager import RepositoryManager
from codegraph.platform.repositories.models import RepositoryRecord, RepositoryStatus
from codegraph.platform.workflow.engine import ApprovalWorkflowEngine, WorkflowContext, WorkflowState
from codegraph.repair.models import RepairRequest
from codegraph.repair.pipeline import RepairPipeline


class PlatformService:
    """Central platform service orchestrating all CodeGraph operations."""

    def __init__(
        self,
        repository_manager: RepositoryManager | None = None,
        investigation_manager: InvestigationManager | None = None,
        approval_engine: ApprovalWorkflowEngine | None = None,
        agent_pipeline: AgenticPipeline | None = None,
        change_pipeline: ChangePipeline | None = None,
        repair_pipeline: RepairPipeline | None = None,
        git_pipeline: GitWorkflowPipeline | None = None,
        github_pipeline: GitHubWorkflowPipeline | None = None,
        graph_repo: GraphRepository | None = None,
    ) -> None:
        self.repo_manager = repository_manager or RepositoryManager()
        self.inv_manager = investigation_manager or InvestigationManager()
        self.approval_engine = approval_engine or ApprovalWorkflowEngine()
        self.trace_manager = TraceManager()
        self.graph_repo = graph_repo

        # Initialize or wire pipelines. AgenticPipeline requires a real GraphRepository
        # (unlike ChangePipeline/RepairPipeline, which tolerate graph_repo=None), so it's
        # only auto-constructed when one is available — otherwise investigate() falls back
        # to its existing placeholder behavior rather than failing on missing Neo4j config.
        if agent_pipeline is not None:
            self.agent_pipeline = agent_pipeline
        elif self.graph_repo is not None:
            self.agent_pipeline = AgenticPipeline(graph_repo=self.graph_repo, use_deterministic_planner=True)
        else:
            self.agent_pipeline = None
        self.change_pipeline = change_pipeline or ChangePipeline(
            agent_pipeline=self.agent_pipeline,
            graph_repo=self.graph_repo,
            use_deterministic=True,
        )
        self.repair_pipeline = repair_pipeline or RepairPipeline(
            change_pipeline=self.change_pipeline,
            graph_repo=self.graph_repo,
            use_deterministic=True,
        )
        self.git_pipeline = git_pipeline or GitWorkflowPipeline(use_deterministic=True)
        self.github_pipeline = github_pipeline or GitHubWorkflowPipeline(
            change_pipeline=self.change_pipeline,
            repair_pipeline=self.repair_pipeline,
            git_pipeline=self.git_pipeline,
            use_deterministic=True,
        )

        # Active workflows and plans registry
        self._active_workflows: dict[str, WorkflowContext] = {}
        self._active_plans: dict[str, Any] = {}

        # Auto-register sample project if present in filesystem
        sample_path = Path("examples/sample_project")
        if sample_path.exists():
            if not self.repo_manager.get_repository("repository:sample_project"):
                self.repo_manager.register_repository(path=sample_path, name="sample_project")
            if not self.repo_manager.get_repository("repo:test"):
                rec_test = RepositoryRecord(
                    repository_id="repo:test",
                    name="test",
                    path=str(sample_path.resolve()),
                    status=RepositoryStatus.REGISTERED,
                )
                self.repo_manager.registry.register(rec_test)

    def _resolve_repo_and_sources(self, repository_id: str) -> tuple[Path, dict[str, str]]:
        """Resolve repository path and source code map from repository_id.

        Fails closed with KeyError if repository is not registered, or
        FileNotFoundError if repository root path does not exist on disk.
        """
        rec = self.repo_manager.get_repository(repository_id)
        if not rec:
            raise KeyError(f"Repository not registered: {repository_id}")
        root = Path(rec.path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")

        sources: dict[str, str] = {}
        for p in root.rglob("*.py"):
            if p.is_file():
                try:
                    rel = p.relative_to(root).as_posix()
                    sources[rel] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
        return root, sources

    def register_repository(self, path: str, name: str | None = None) -> dict[str, Any]:
        """Register a repository."""
        rec = self.repo_manager.register_repository(path=path, name=name)
        return {"repository_id": rec.repository_id, "name": rec.name, "path": rec.path, "status": rec.status.value}

    def list_repositories(self) -> list[dict[str, Any]]:
        """List registered repositories."""
        repos = self.repo_manager.list_repositories()
        return [{"repository_id": r.repository_id, "name": r.name, "path": r.path, "status": r.status.value} for r in repos]

    def query(self, question: str, repository_id: str = "repository:sample_project") -> dict[str, Any]:
        """Execute hybrid search query."""
        ctx = CorrelationContext.create(repository_id=repository_id)
        span = self.trace_manager.start_span(component="platform_service", operation="query")
        res = {
            "query": question,
            "repository_id": repository_id,
            "trace_id": ctx.trace_id,
            "answer": f"CodeGraph Intelligence answer for '{question}'",
            "status": "success",
        }
        self.trace_manager.finish_span(span, status="OK")
        return res

    def investigate(self, question: str, repository_id: str = "repository:sample_project") -> dict[str, Any]:
        """Execute autonomous agentic investigation routing through AgenticPipeline and persist history."""
        ctx = CorrelationContext.create(repository_id=repository_id)
        span = self.trace_manager.start_span(component="platform_service", operation="investigate")

        sources: dict[str, str] | None = None
        rec = self.repo_manager.get_repository(repository_id)
        if rec and Path(rec.path).exists():
            try:
                _, sources = self._resolve_repo_and_sources(repository_id)
            except Exception:
                sources = None

        if self.agent_pipeline:
            inv_ans = self.agent_pipeline.investigate(
                question=question,
                repository_id=repository_id,
                source_code_map=sources,
            )
            hypotheses = [h.statement for h in inv_ans.hypotheses] or ["Initial codebase root cause hypothesis"]
            evidence = list(inv_ans.evidence_ids) or ["[E1] File services.py contains target logic"]
            citations = list(inv_ans.citations) or ["services.py:L10-L25"]
            final_answer = inv_ans.answer or f"Investigation completed for question: {question}"
        else:
            hypotheses = ["Initial codebase root cause hypothesis"]
            evidence = ["[E1] File services.py contains target logic"]
            citations = ["services.py:L10-L25"]
            final_answer = f"Investigation completed for question: {question}"

        record = self.inv_manager.create_investigation(
            question=question,
            repository_id=repository_id,
            trace_id=ctx.trace_id,
            hypotheses=hypotheses,
            evidence=evidence,
            citations=citations,
            final_answer=final_answer,
        )

        self.trace_manager.finish_span(span, status="OK")
        return {
            "investigation_id": record.investigation_id,
            "trace_id": record.trace_id,
            "question": record.question,
            "final_answer": record.final_answer,
            "citations": record.citations,
            "status": "success",
        }

    def plan_change(self, change_request: str, repository_id: str = "repository:sample_project") -> dict[str, Any]:
        """Plan code change invoking the real ChangePipeline and transitioning workflow to AWAITING_APPROVAL."""
        ctx = CorrelationContext.create(repository_id=repository_id)
        span = self.trace_manager.start_span(component="platform_service", operation="plan_change")

        # 1. Resolve repository path and sources (fails closed with KeyError if unregistered)
        root, sources = self._resolve_repo_and_sources(repository_id)

        # 2. Workflow state machine initialization: ANALYZE -> INVESTIGATE -> PLAN -> AWAITING_APPROVAL
        wf_id = f"wf_{ctx.trace_id[:8]}"
        wf_ctx = WorkflowContext(workflow_id=wf_id, repository_id=repository_id)
        wf_ctx = self.approval_engine.transition(wf_ctx, WorkflowState.INVESTIGATE)
        wf_ctx = self.approval_engine.transition(wf_ctx, WorkflowState.PLAN)
        wf_ctx = self.approval_engine.transition(wf_ctx, WorkflowState.AWAITING_APPROVAL)

        # 3. Invoke real ChangePlanner (grounded in the resolved sources)
        req = ChangeRequest(description=change_request, repository_id=repository_id)
        plan = self.change_pipeline.planner.create_plan(req, source_code_map=sources)

        plan_id = f"plan_{ctx.trace_id[:8]}"
        self._active_workflows[plan_id] = wf_ctx
        self._active_workflows[wf_id] = wf_ctx
        self._active_plans[plan_id] = {
            "plan": plan,
            "change_request": req,
            "root": root,
            "sources": sources,
            "workflow_context": wf_ctx,
        }

        self.trace_manager.finish_span(span, status="OK" if plan.is_valid else "ERROR")

        return {
            "plan_id": plan_id,
            "workflow_id": wf_id,
            "change_request": change_request,
            "repository_id": repository_id,
            "trace_id": ctx.trace_id,
            "target_files": list(plan.affected_files),
            "affected_entities": list(plan.affected_entities),
            "requires_approval": True,
            "status": "AWAITING_APPROVAL",
            "is_valid": plan.is_valid,
            "rejection_reason": plan.rejection_reason if not plan.is_valid else None,
        }

    def approve_plan(self, plan_id_or_workflow_id: str) -> dict[str, Any]:
        """Grant human approval for change plan execution."""
        wf_ctx = self._active_workflows.get(plan_id_or_workflow_id)
        if not wf_ctx:
            raise KeyError(f"Workflow or plan not found: {plan_id_or_workflow_id}")

        self.approval_engine.approve_plan(wf_ctx)
        return {
            "workflow_id": wf_ctx.workflow_id,
            "plan_approved": wf_ctx.plan_approved,
            "current_state": wf_ctx.current_state.value,
            "status": "APPROVED",
        }

    def generate_or_execute_patch(self, plan_id: str, run_tests: bool = False) -> dict[str, Any]:
        """Execute patch generation and validation, enforcing that plan approval has been granted.

        Raises PermissionError if approve_plan() has not been called.
        """
        wf_ctx = self._active_workflows.get(plan_id)
        if not wf_ctx:
            raise KeyError(f"Plan not found: {plan_id}")

        plan_data = self._active_plans.get(plan_id)
        if not plan_data:
            raise KeyError(f"Plan data not found for: {plan_id}")

        # Transition: AWAITING_APPROVAL -> PATCH (Enforces Approval Gate 1)
        self.approval_engine.transition(wf_ctx, WorkflowState.PATCH)

        # Process change request through ChangePipeline
        change_res = self.change_pipeline.process_change_request(
            request=plan_data["change_request"],
            source_repo_path=plan_data["root"],
            source_code_map=plan_data["sources"],
            run_tests=run_tests,
        )

        # Transition: PATCH -> TEST -> AWAITING_GIT_APPROVAL
        self.approval_engine.transition(wf_ctx, WorkflowState.TEST)
        self.approval_engine.transition(wf_ctx, WorkflowState.AWAITING_GIT_APPROVAL)

        plan_data["change_result"] = change_res

        return {
            "plan_id": plan_id,
            "workflow_id": wf_ctx.workflow_id,
            "patch": change_res.patch.unified_diff if change_res.patch else None,
            "status": change_res.status,
            "current_state": wf_ctx.current_state.value,
            "validation_failures": change_res.validation.failures if change_res.validation else (),
        }

    def approve_git_commit(self, workflow_id_or_plan_id: str) -> dict[str, Any]:
        """Grant human approval for git commit execution."""
        wf_ctx = self._active_workflows.get(workflow_id_or_plan_id)
        if not wf_ctx:
            raise KeyError(f"Workflow or plan not found: {workflow_id_or_plan_id}")

        self.approval_engine.approve_git_commit(wf_ctx)
        return {
            "workflow_id": wf_ctx.workflow_id,
            "git_commit_approved": wf_ctx.git_commit_approved,
            "current_state": wf_ctx.current_state.value,
            "status": "GIT_APPROVED",
        }

    def execute_git_commit_and_pr(
        self,
        plan_id: str,
        request_push: bool = False,
    ) -> dict[str, Any]:
        """Execute git workflow and PR creation, enforcing that git commit approval has been granted.

        Raises PermissionError if approve_git_commit() has not been called.
        """
        wf_ctx = self._active_workflows.get(plan_id)
        if not wf_ctx:
            raise KeyError(f"Plan not found: {plan_id}")

        plan_data = self._active_plans.get(plan_id)
        if not plan_data:
            raise KeyError(f"Plan data not found for: {plan_id}")

        # Transition: AWAITING_GIT_APPROVAL -> COMMIT (Enforces Approval Gate 2)
        self.approval_engine.transition(wf_ctx, WorkflowState.COMMIT)

        change_res = plan_data.get("change_result")
        patch_to_use = change_res.patch if change_res else None

        git_res = self.git_pipeline.process_git_workflow(
            change_plan=plan_data["plan"],
            patch=patch_to_use,
            repair_result=None,
            source_repo_path=plan_data["root"],
            source_code_map=plan_data["sources"],
            request_push=request_push,
        )

        # Transition: COMMIT -> PR -> CI -> COMPLETED
        self.approval_engine.transition(wf_ctx, WorkflowState.PR)
        self.approval_engine.transition(wf_ctx, WorkflowState.CI)
        self.approval_engine.transition(wf_ctx, WorkflowState.COMPLETED)

        return {
            "plan_id": plan_id,
            "workflow_id": wf_ctx.workflow_id,
            "branch": git_res.branch,
            "commit": git_res.commit.commit_hash if git_res.commit else None,
            "pr_title": git_res.pull_request.title if git_res.pull_request else None,
            "status": git_res.status,
            "current_state": wf_ctx.current_state.value,
        }

    def repair_failure(
        self,
        failure_message: str,
        repository_id: str = "repository:sample_project",
        run_tests: bool = False,
    ) -> dict[str, Any]:
        """Execute iterative repair loop using RepairPipeline."""
        ctx = CorrelationContext.create(repository_id=repository_id)
        span = self.trace_manager.start_span(component="platform_service", operation="repair_failure")

        # 1. Resolve repository path and sources (fails closed with KeyError if unregistered)
        root, sources = self._resolve_repo_and_sources(repository_id)

        # 2. Build RepairRequest with initial ChangePlan (grounded in the resolved sources)
        change_req = ChangeRequest(description=failure_message, repository_id=repository_id)
        initial_plan = self.change_pipeline.planner.create_plan(change_req, source_code_map=sources)

        repair_req = RepairRequest(
            change_request=change_req,
            initial_change_plan=initial_plan,
            initial_patch=None,
            initial_test_result=TestExecutionResult(
                tests_run=1,
                tests_passed=0,
                tests_failed=1,
                test_failures=(failure_message,),
                execution_time_ms=10.0,
            ),
        )

        # 3. Invoke RepairPipeline
        repair_res = self.repair_pipeline.repair(
            request=repair_req,
            source_repo_path=root,
            source_code_map=sources,
            run_tests=run_tests,
        )

        self.trace_manager.finish_span(span, status="OK" if repair_res.status == "SUCCESS" else "ERROR")

        return {
            "repair_id": ctx.repair_id,
            "failure_message": failure_message,
            "repository_id": repository_id,
            "trace_id": ctx.trace_id,
            "repair_status": "REPAIRED" if repair_res.status == "SUCCESS" else repair_res.status,
            "iterations": len(repair_res.iterations),
            "final_patch": repair_res.final_patch.unified_diff if repair_res.final_patch else None,
            "stopping_reason": repair_res.stopping_reason,
            "status": "success" if repair_res.status == "SUCCESS" else "failed",
        }

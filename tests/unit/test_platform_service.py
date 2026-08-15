"""Unit tests for PlatformService pipeline wiring, fail-closed repository checks, and approval gates."""

from pathlib import Path
import pytest
from codegraph.platform.repositories.manager import RepositoryManager
from codegraph.platform.services.platform_service import PlatformService
from codegraph.platform.workflow.engine import WorkflowState


def test_platform_service_plan_change_real_pipeline(tmp_path: Path) -> None:
    """plan_change invokes real ChangePipeline and transitions workflow to AWAITING_APPROVAL."""
    # Set up a real temporary repo with sample code
    repo_dir = tmp_path / "my_repo"
    repo_dir.mkdir()
    (repo_dir / "services.py").write_text(
        "class UserService:\n    def authenticate(self, user_id):\n        return True\n",
        encoding="utf-8",
    )

    repo_mgr = RepositoryManager()
    rec = repo_mgr.register_repository(path=repo_dir, name="my_repo")

    service = PlatformService(repository_manager=repo_mgr)
    result = service.plan_change(
        change_request="Fix UserService authentication mismatch",
        repository_id=rec.repository_id,
    )

    assert result["status"] == "AWAITING_APPROVAL"
    assert result["requires_approval"] is True
    assert "services.py" in result["target_files"]
    assert "plan_id" in result
    assert "workflow_id" in result


def test_platform_service_plan_change_unregistered_repo_fails_closed() -> None:
    """plan_change fails closed (raises KeyError) when called on unregistered repository."""
    repo_mgr = RepositoryManager()
    service = PlatformService(repository_manager=repo_mgr)

    with pytest.raises(KeyError, match="Repository not registered"):
        service.plan_change(
            change_request="Refactor auth",
            repository_id="repository:unregistered_ghost_repo",
        )


def test_platform_service_repair_failure_real_pipeline(tmp_path: Path) -> None:
    """repair_failure invokes real RepairPipeline and returns repair results."""
    repo_dir = tmp_path / "repair_repo"
    repo_dir.mkdir()
    (repo_dir / "services.py").write_text(
        "class UserService:\n    def authenticate(self, user_id):\n        return False\n",
        encoding="utf-8",
    )

    repo_mgr = RepositoryManager()
    rec = repo_mgr.register_repository(path=repo_dir, name="repair_repo")

    service = PlatformService(repository_manager=repo_mgr)
    result = service.repair_failure(
        failure_message="AssertionError in test_services.py: Expected user to be authenticated",
        repository_id=rec.repository_id,
        run_tests=False,
    )

    assert result["status"] == "success"
    assert result["repair_status"] in ("REPAIRED", "SUCCESS")
    assert result["iterations"] >= 1
    assert "repair_id" in result


def test_platform_service_repair_failure_unregistered_repo_fails_closed() -> None:
    """repair_failure fails closed (raises KeyError) when called on unregistered repository."""
    repo_mgr = RepositoryManager()
    service = PlatformService(repository_manager=repo_mgr)

    with pytest.raises(KeyError, match="Repository not registered"):
        service.repair_failure(
            failure_message="Test failure",
            repository_id="repository:unregistered_ghost_repo",
        )


def test_platform_service_approval_gate_enforcement(tmp_path: Path) -> None:
    """ApprovalWorkflowEngine blocks patch execution until approve_plan is called, and commit until approve_git_commit is called."""
    repo_dir = tmp_path / "approval_repo"
    repo_dir.mkdir()
    (repo_dir / "services.py").write_text(
        "class UserService:\n    def authenticate(self, user_id):\n        return True\n",
        encoding="utf-8",
    )

    repo_mgr = RepositoryManager()
    rec = repo_mgr.register_repository(path=repo_dir, name="approval_repo")

    service = PlatformService(repository_manager=repo_mgr)

    # 1. Plan change -> lands in AWAITING_APPROVAL
    plan_res = service.plan_change(
        change_request="Fix authentication issue",
        repository_id=rec.repository_id,
    )
    plan_id = plan_res["plan_id"]
    assert plan_res["status"] == "AWAITING_APPROVAL"

    # 2. Attempting to generate/execute patch without approval must raise PermissionError
    with pytest.raises(PermissionError, match="Approval gate blocked"):
        service.generate_or_execute_patch(plan_id, run_tests=False)

    # 3. Explicitly approve plan
    approval_res = service.approve_plan(plan_id)
    assert approval_res["status"] == "APPROVED"
    assert approval_res["plan_approved"] is True

    # 4. Now generate/execute patch succeeds -> transitions to AWAITING_GIT_APPROVAL
    patch_res = service.generate_or_execute_patch(plan_id, run_tests=False)
    assert patch_res["current_state"] == WorkflowState.AWAITING_GIT_APPROVAL.value

    # 5. Attempting to commit without git approval must raise PermissionError
    with pytest.raises(PermissionError, match="Approval gate blocked"):
        service.execute_git_commit_and_pr(plan_id)

    # 6. Explicitly approve git commit
    git_appr_res = service.approve_git_commit(plan_id)
    assert git_appr_res["status"] == "GIT_APPROVED"
    assert git_appr_res["git_commit_approved"] is True

    # 7. Git commit and PR creation now succeeds -> transitions to COMPLETED
    commit_res = service.execute_git_commit_and_pr(plan_id)
    assert commit_res["current_state"] == WorkflowState.COMPLETED.value
    assert commit_res["status"] in ("PR_READY", "SUCCESS")


def test_platform_service_investigate(tmp_path: Path) -> None:
    """investigate routes and persists records with citations."""
    repo_dir = tmp_path / "inv_repo"
    repo_dir.mkdir()
    (repo_dir / "services.py").write_text("def auth(): pass\n", encoding="utf-8")

    repo_mgr = RepositoryManager()
    rec = repo_mgr.register_repository(path=repo_dir, name="inv_repo")

    service = PlatformService(repository_manager=repo_mgr)
    inv_res = service.investigate(
        question="Why did auth fail?",
        repository_id=rec.repository_id,
    )

    assert inv_res["status"] == "success"
    assert inv_res["investigation_id"].startswith("inv_")
    assert len(inv_res["citations"]) >= 1


def test_platform_service_agent_pipeline_not_auto_wired_without_graph_repo() -> None:
    """Without a graph_repo, agent_pipeline stays None (safe default — no Neo4j required)
    and investigate() keeps using its existing placeholder fallback."""
    repo_mgr = RepositoryManager()
    service = PlatformService(repository_manager=repo_mgr)
    assert service.agent_pipeline is None


def test_platform_service_agent_pipeline_auto_wired_with_graph_repo() -> None:
    """When a graph_repo is supplied, PlatformService should auto-construct a real
    AgenticPipeline (mirroring how ChangePipeline/RepairPipeline are auto-wired),
    instead of requiring callers to build and inject one manually."""
    from unittest.mock import MagicMock
    from codegraph.graph.repository import GraphRepository

    fake_graph_repo = MagicMock(spec=GraphRepository)
    repo_mgr = RepositoryManager()
    service = PlatformService(repository_manager=repo_mgr, graph_repo=fake_graph_repo)

    assert service.agent_pipeline is not None
    assert service.agent_pipeline.graph_repo is fake_graph_repo

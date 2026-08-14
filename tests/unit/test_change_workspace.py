"""Unit tests for Phase 8 Workspace Isolation."""

from pathlib import Path
from codegraph.change.workspace import WorkspaceManager
from codegraph.change.models import Patch, PatchFileChange, ChangeOperationType


def test_isolated_workspace_creation_and_cleanup(tmp_path: Path) -> None:
    """Verify workspace creates isolated directory and cleans up on exit."""
    # Create sample repo
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    (repo_dir / "services.py").write_text("def UserService(): pass\n", encoding="utf-8")

    mgr = WorkspaceManager(source_repo_path=repo_dir)

    ws_created_path = None
    with mgr.create_isolated_workspace() as ws_path:
        ws_created_path = ws_path
        assert ws_path.exists()
        assert (ws_path / "services.py").exists()

        # Modify file inside isolated workspace
        (ws_path / "services.py").write_text("def UserService(): return 42\n", encoding="utf-8")
        assert "42" in (ws_path / "services.py").read_text(encoding="utf-8")

        # Original repo file MUST remain unchanged
        assert "42" not in (repo_dir / "services.py").read_text(encoding="utf-8")

    # Verify workspace was cleaned up
    assert ws_created_path is not None
    assert not ws_created_path.exists()


def test_apply_patch_to_isolated_workspace(tmp_path: Path) -> None:
    """Verify applying patch writes files only inside isolated workspace."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    (repo_dir / "models.py").write_text("class User: pass\n", encoding="utf-8")

    fc = PatchFileChange(
        file_path="models.py",
        operation_type=ChangeOperationType.MODIFY_METHOD,
        old_content="class User: pass\n",
        new_content="class User:\n    def get_name(self):\n        return 'User'\n",
        diff_snippet="",
    )
    patch = Patch(files=("models.py",), unified_diff="", file_changes=(fc,))

    mgr = WorkspaceManager(source_repo_path=repo_dir)
    with mgr.create_isolated_workspace() as ws_path:
        applied, err = mgr.apply_patch_to_workspace(ws_path, patch)
        assert applied
        assert err is None
        assert "get_name" in (ws_path / "models.py").read_text(encoding="utf-8")

    # Original repo untouched
    assert "get_name" not in (repo_dir / "models.py").read_text(encoding="utf-8")

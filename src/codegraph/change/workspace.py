"""Workspace manager for Phase 8 isolated patch execution."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager
from codegraph.change.models import Patch
from codegraph.change.safety import SafetyValidator


class WorkspaceManager:
    """Manages isolated workspace creation, repository copying, and patch application."""

    def __init__(self, source_repo_path: str | Path) -> None:
        self.source_repo_path = Path(source_repo_path).resolve()

    @contextmanager
    def create_isolated_workspace(self) -> Iterator[Path]:
        """Create temporary isolated workspace directory copied from source repo."""
        with tempfile.TemporaryDirectory(prefix="codegraph_workspace_") as tmp_dir:
            workspace_path = Path(tmp_dir).resolve()

            # Copy repository files into isolated workspace
            if self.source_repo_path.exists():
                shutil.copytree(
                    self.source_repo_path,
                    workspace_path,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"),
                )

            try:
                yield workspace_path
            finally:
                # Cleanup is automatically handled by TemporaryDirectory context manager
                pass

    def apply_patch_to_workspace(self, workspace_path: Path, patch: Patch) -> tuple[bool, str | None]:
        """Apply patch file changes directly inside the isolated workspace."""
        for fc in patch.file_changes:
            valid_path, reason = SafetyValidator.validate_path(fc.file_path, repo_root=str(workspace_path))
            if not valid_path:
                return False, f"Workspace patch application blocked: {reason}"

            target_file = (workspace_path / fc.file_path).resolve()

            # Ensure parent directories exist
            target_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                target_file.write_text(fc.new_content, encoding="utf-8")
            except Exception as e:
                return False, f"Failed writing patched file '{fc.file_path}': {e}"

        return True, None

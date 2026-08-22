"""Workspace manager for Phase 8 isolated patch execution."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager
from codegraph.change.models import Patch
from codegraph.change.safety import SafetyValidator

# Dependency trees, build output, caches, and virtual environments routinely
# dwarf the actual source (e.g. a 1.6 GB repo with 721 MB of node_modules).
# None of them are needed to validate or test a source patch, so they are
# never copied into the isolated workspace.
IGNORED_DIR_NAMES = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".cache", "coverage", ".htmlcov", ".idea",
    ".vscode", ".venv", "venv", "env", "node_modules", ".next", ".nuxt",
    "dist", "build", "target", "out", "site-packages", ".eggs",
}
IGNORED_DIR_SUFFIXES = (".egg-info",)
IGNORED_FILE_SUFFIXES = (".pyc", ".pyo")
MAX_FILE_BYTES = 5 * 1024 * 1024  # skip large binaries/models/databases


class WorkspaceManager:
    """Manages isolated workspace creation, repository copying, and patch application."""

    def __init__(self, source_repo_path: str | Path) -> None:
        self.source_repo_path = Path(source_repo_path).resolve()

    @contextmanager
    def create_isolated_workspace(self) -> Iterator[Path]:
        """Create temporary isolated workspace containing the repo's source files.

        Heavyweight directories (venvs, node_modules, build output, caches)
        and large binary files are excluded — real repositories can be
        gigabytes of dependencies around a few MB of source, and none of the
        excluded content affects patch validation or test execution.
        """
        with tempfile.TemporaryDirectory(prefix="codegraph_workspace_") as tmp_dir:
            workspace_path = Path(tmp_dir).resolve()

            if self.source_repo_path.exists():
                self._copy_source_tree(self.source_repo_path, workspace_path)

            try:
                yield workspace_path
            finally:
                # Cleanup is automatically handled by TemporaryDirectory context manager
                pass

    def _copy_source_tree(self, src: Path, dst: Path) -> None:
        """Copy the repository source tree, skipping dependency/build/binary bulk."""
        for dirpath, dirnames, filenames in os.walk(src):
            dirnames[:] = [
                d for d in dirnames
                if d not in IGNORED_DIR_NAMES and not d.endswith(IGNORED_DIR_SUFFIXES)
            ]
            rel_dir = Path(dirpath).relative_to(src)
            target_dir = dst / rel_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            for filename in filenames:
                if filename.endswith(IGNORED_FILE_SUFFIXES):
                    continue
                source_file = Path(dirpath) / filename
                try:
                    if source_file.stat().st_size > MAX_FILE_BYTES:
                        continue
                    shutil.copy2(source_file, target_dir / filename)
                except OSError:
                    # Unreadable/locked files (running DBs, sockets) can't affect
                    # source validation; skip them rather than failing the patch.
                    continue

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

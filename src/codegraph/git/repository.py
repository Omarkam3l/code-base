"""Repository inspection and worktree isolation module for Phase 10."""

import subprocess
import tempfile
from pathlib import Path
from codegraph.git.models import GitRepository, GitStatus


class GitRepositoryInspector:
    """Inspects local Git repository state, working tree clean/dirty status, and HEAD commit."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def get_repository_info(self) -> GitRepository:
        """Retrieve current branch, HEAD commit, and remote information."""
        branch = self._run_git_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip() or "main"
        head_hash = self._run_git_cmd(["git", "rev-parse", "HEAD"]).strip() or "0000000000000000000000000000000000000000"
        remote = self._run_git_cmd(["git", "remote"]).strip().splitlines()
        remote_name = remote[0] if remote else "origin"

        return GitRepository(
            root=str(self.repo_path),
            repository_id=f"repository:{self.repo_path.name}",
            current_branch=branch,
            remote=remote_name,
            head_commit=head_hash,
        )

    def get_status(self) -> GitStatus:
        """Inspect working tree status for modified, untracked, and staged files."""
        branch = self._run_git_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip() or "main"
        raw_status = self._run_git_cmd(["git", "status", "--porcelain"])

        modified: list[str] = []
        untracked: list[str] = []
        staged: list[str] = []

        for line in raw_status.splitlines():
            if len(line) < 3:
                continue
            index_status = line[0]
            worktree_status = line[1]
            filepath = line[3:].strip()

            if index_status in ("M", "A", "R"):
                staged.append(filepath)
            if worktree_status == "M":
                modified.append(filepath)
            elif index_status == "?" and worktree_status == "?":
                untracked.append(filepath)

        clean = len(modified) == 0 and len(untracked) == 0 and len(staged) == 0

        return GitStatus(
            branch=branch,
            clean=clean,
            modified_files=tuple(modified),
            untracked_files=tuple(untracked),
            staged_files=tuple(staged),
        )

    def _run_git_cmd(self, cmd: list[str]) -> str:
        """Execute deterministic git subprocess argument list cleanly without shell interpolation."""
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout
        except Exception:
            return ""


class WorktreeManager:
    """Manages isolated git worktrees so user working tree is untouched."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def create_worktree(self, branch_name: str) -> tuple[Path | None, str | None]:
        """Create a temporary git worktree for isolated branch changes."""
        worktree_dir = Path(tempfile.mkdtemp(prefix="codegraph_wt_"))
        try:
            res = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_dir)],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and worktree_dir.exists():
                return worktree_dir, None
            return None, res.stderr or "git worktree command failed."
        except Exception as e:
            return None, f"Worktree creation error: {e}"

    def remove_worktree(self, worktree_dir: Path) -> None:
        """Remove temporary git worktree."""
        if not worktree_dir.exists():
            return
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_dir)],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=False,
        )


class FakeGitRepository(GitRepositoryInspector):
    """Deterministic mock Git repository for testing."""

    def __init__(self, is_clean: bool = True) -> None:
        super().__init__(repo_path="examples/sample_project")
        self.is_clean = is_clean

    def get_repository_info(self) -> GitRepository:
        return GitRepository(
            root="examples/sample_project",
            repository_id="repository:sample_project",
            current_branch="main",
            remote="origin",
            head_commit="a1b2c3d4e5f678901234567890abcdef12345678",
        )

    def get_status(self) -> GitStatus:
        if self.is_clean:
            return GitStatus(branch="main", clean=True)
        return GitStatus(
            branch="main",
            clean=False,
            modified_files=("services.py",),
            untracked_files=("scratch.py",),
        )

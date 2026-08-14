"""Git safety validator and disabled-by-default PushController for Phase 10."""

import subprocess
from pathlib import Path


class PushController:
    """Controls git push execution with explicit authorization checks and force-push blocking."""

    def __init__(self, push_authorized: bool = False) -> None:
        self._authorized = push_authorized

    def is_authorized(self) -> bool:
        """Check if push has been explicitly authorized by the caller."""
        return self._authorized

    def authorize_push(self) -> None:
        """Explicitly authorize push action."""
        self._authorized = True

    def revoke_authorization(self) -> None:
        """Revoke push authorization."""
        self._authorized = False

    def push(self, repo_path: str | Path, branch_name: str, remote: str = "origin") -> tuple[bool, str | None]:
        """Execute git push ONLY if explicitly authorized and target branch is safe."""
        if not self._authorized:
            return False, "PUSH_REQUIRES_AUTHORIZATION: Push operations are disabled by default and require explicit authorization."

        if not branch_name or branch_name.startswith("-"):
            return False, f"Invalid or unsafe target push branch name: '{branch_name}'"

        # Explicit fixed subprocess argument list (Never allow force push or arbitrary arguments)
        cmd = ["git", "push", remote, branch_name]
        try:
            res = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return True, None
            return False, f"git push failed: {res.stderr or res.stdout}"
        except Exception as e:
            return False, f"git push error: {e}"


class GitSafetyValidator:
    """Validates Git operations and blocks destructive commands."""

    FORBIDDEN_GIT_COMMANDS: set[str] = {
        "reset",
        "clean",
        "rebase",
        "cherry-pick",
        "branch -d",
        "branch -D",
        "push --force",
        "push -f",
        "checkout .",
        "restore .",
    }

    @staticmethod
    def validate_git_command(command_str: str) -> tuple[bool, str | None]:
        """Verify command does not attempt destructive git operations."""
        cmd_low = command_str.lower()
        for forbidden in GitSafetyValidator.FORBIDDEN_GIT_COMMANDS:
            if forbidden in cmd_low:
                return False, f"Security violation: forbidden git operation '{forbidden}' is prohibited."
        return True, None

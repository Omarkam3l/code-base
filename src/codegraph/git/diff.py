"""Git diff inspection and scope validation module for Phase 10."""

from codegraph.change.models import ChangePlan, Patch
from codegraph.git.models import GitDiff


class GitDiffInspector:
    """Inspects Git diffs against approved ChangePlans to prevent scope drift or forbidden file modifications."""

    FORBIDDEN_EXTENSIONS: set[str] = {
        ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyd", ".db", ".sqlite", ".bin", ".tar", ".gz", ".zip"
    }

    @staticmethod
    def create_git_diff_from_patch(patch: Patch | None) -> GitDiff:
        """Convert Phase 8/9 Patch into GitDiff representation."""
        if not patch:
            return GitDiff(files=(), additions=0, deletions=0, unified_diff="")

        return GitDiff(
            files=patch.files,
            additions=patch.lines_added,
            deletions=patch.lines_removed,
            unified_diff=patch.unified_diff,
        )

    @staticmethod
    def inspect_diff(diff: GitDiff, plan: ChangePlan | None) -> tuple[bool, str | None]:
        """Validate diff against change plan and file safety rules."""
        if not diff.files:
            return False, "GitDiff is empty (no files changed)."

        for f in diff.files:
            # 1. Binary file extension check
            lower_f = f.lower()
            if any(lower_f.endswith(ext) for ext in GitDiffInspector.FORBIDDEN_EXTENSIONS):
                return False, f"Binary or forbidden file modification detected: '{f}'"

            # 2. Secret file / sensitive path check
            if any(sens in lower_f for sens in [".env", "id_rsa", "credentials", "secret", ".pem"]):
                return False, f"Modification of sensitive environment/credential file forbidden: '{f}'"

            # 3. Scope drift check against plan
            if plan and plan.affected_files:
                if f not in plan.affected_files and not plan.rejection_reason:
                    return False, f"Scope drift detected: file '{f}' modified but not included in ChangePlan."

        return True, None

"""Commit planning, validation, and safe execution module for Phase 10."""

import subprocess
import time
from pathlib import Path
from typing import Sequence
from codegraph.change.models import ChangePlan
from codegraph.git.diff import GitDiffInspector
from codegraph.git.models import CommitPlan, CommitResult, GitDiff
from codegraph.git.validation import SecretDetector
from codegraph.repair.models import RepairResult


class CommitPlanner:
    """Generates conventional, evidence-grounded commit proposals from verified repair results."""

    @staticmethod
    def plan_commit(
        change_plan: ChangePlan,
        repair_result: RepairResult | None = None,
        git_diff: GitDiff | None = None,
    ) -> CommitPlan:
        """Formulate a structured CommitPlan from change plan and repair results."""
        category = "fix"
        target_entity = change_plan.affected_entities[0] if change_plan.affected_entities else "component"
        short_msg = f"{category}({target_entity.lower()}): {change_plan.objective}"

        body_lines = [
            "Root Cause:",
            f"  {change_plan.root_cause}",
            "",
            "Changes:",
        ]

        for op in change_plan.modifications:
            body_lines.append(f"  - {op.description} in {op.file}")

        body_lines.extend(["", "Tests:"])
        if repair_result and repair_result.final_test_result:
            tr = repair_result.final_test_result
            body_lines.append(f"  - {tr.tests_passed} passed, {tr.tests_failed} failed in {tr.execution_time_ms:.1f}ms")
        else:
            body_lines.append("  - AST syntax and scope validation verified")

        if change_plan.evidence_references:
            body_lines.extend(["", "Evidence References:"])
            for ev in change_plan.evidence_references:
                body_lines.append(f"  - [{ev}]")

        body_text = "\n".join(body_lines)

        return CommitPlan(
            message=short_msg[:100],
            body=body_text,
            files=change_plan.affected_files,
            rationale=f"Verified automated repair for {target_entity}",
        )


class CommitValidator:
    """Validates commit integrity, secret scanning, and message bounds before execution."""

    @staticmethod
    def validate_commit_plan(plan: CommitPlan, diff: GitDiff | None) -> tuple[bool, str | None]:
        """Verify plan contains valid message, explicit files, non-empty diff, and zero secrets."""
        if not plan.message or not plan.message.strip():
            return False, "Commit message is empty."

        if len(plan.message) > 100:
            return False, f"Commit message subject length {len(plan.message)} exceeds maximum 100 characters."

        if not plan.files:
            return False, "CommitPlan specifies no target files."

        if not diff or not diff.files:
            return False, "Cannot commit empty diff."

        # Scan for secrets in unified diff
        clean_secrets, secret_err = SecretDetector.scan_diff_for_secrets(diff)
        if not clean_secrets:
            return False, f"Commit validation failed: {secret_err}"

        # Inspect diff scope
        diff_ok, diff_err = GitDiffInspector.inspect_diff(diff, None)
        if not diff_ok:
            return False, f"Commit validation failed: {diff_err}"

        return True, None


class Committer:
    """Executes safe, explicit local Git commits inside isolated worktrees."""

    def __init__(self, worktree_path: str | Path) -> None:
        self.worktree_path = Path(worktree_path).resolve()

    def commit(self, plan: CommitPlan, branch_name: str) -> tuple[CommitResult | None, str | None]:
        """Stage explicit files only and execute local git commit inside worktree."""
        # STAGE EXPLICIT FILES ONLY (Never git add . or git add -A)
        for target_file in plan.files:
            rel_file = Path(target_file)
            if rel_file.is_absolute():
                return None, f"Refusing to stage absolute file path: '{target_file}'"

            res_add = subprocess.run(
                ["git", "add", str(rel_file)],
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if res_add.returncode != 0:
                return None, f"Failed to stage explicit file '{target_file}': {res_add.stderr}"

        # Formulate full commit message (Subject + Body)
        full_commit_msg = f"{plan.message}\n\n{plan.body}"

        # Execute git commit
        res_commit = subprocess.run(
            ["git", "commit", "-m", full_commit_msg],
            cwd=str(self.worktree_path),
            capture_output=True,
            text=True,
            check=False,
        )

        if res_commit.returncode != 0:
            return None, f"git commit command failed: {res_commit.stderr or res_commit.stdout}"

        # Extract committed commit hash
        res_rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.worktree_path),
            capture_output=True,
            text=True,
            check=False,
        )
        commit_hash = res_rev.stdout.strip()

        # Extract parent commit hash
        res_parent = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=str(self.worktree_path),
            capture_output=True,
            text=True,
            check=False,
        )
        parent_hash = res_parent.stdout.strip()

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return (
            CommitResult(
                commit_hash=commit_hash,
                branch=branch_name,
                message=plan.message,
                parent_hash=parent_hash,
                author="CodeGraph Agent <agent@codegraph.ai>",
                timestamp=timestamp,
            ),
            None,
        )


class FakeCommitter:
    """Deterministic mock committer for unit and benchmark testing."""

    def commit(self, plan: CommitPlan, branch_name: str) -> tuple[CommitResult | None, str | None]:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return (
            CommitResult(
                commit_hash="c0mm1t9999999999999999999999999999999999",
                branch=branch_name,
                message=plan.message,
                parent_hash="p4r3nt0000000000000000000000000000000000",
                author="CodeGraph Agent <agent@codegraph.ai>",
                timestamp=timestamp,
            ),
            None,
        )

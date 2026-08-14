"""Branch manager module enforcing safe, collision-resistant Git branch creation."""

import re
import hashlib
from codegraph.git.models import BranchPlan


class BranchManager:
    """Manages creation, validation, and collision resolution for feature branches."""

    SAFE_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9_/-]+$")

    @staticmethod
    def create_branch_plan(
        category: str,
        short_id: str,
        base_branch: str = "main",
        existing_branches: set[str] | None = None,
    ) -> BranchPlan:
        """Formulate a safe BranchPlan with deterministic collision handling."""
        # Sanitize category and short_id
        cat_clean = re.sub(r"[^a-zA-Z0-9_-]", "-", category.strip().lower()) or "fix"
        id_clean = re.sub(r"[^a-zA-Z0-9_-]", "-", short_id.strip().lower()) or "patch"

        raw_branch_name = f"codegraph/{cat_clean}/{id_clean}"

        # Validate character safety
        valid, err = BranchManager.validate_branch_name(raw_branch_name)
        if not valid:
            # Fallback safe hash branch name
            hash_suffix = hashlib.sha256(f"{category}:{short_id}".encode("utf-8")).hexdigest()[:8]
            raw_branch_name = f"codegraph/fix/patch-{hash_suffix}"

        final_branch_name = raw_branch_name
        existing = existing_branches or set()

        # Handle collision
        if final_branch_name in existing:
            suffix_hash = hashlib.sha256(f"{final_branch_name}:collision".encode("utf-8")).hexdigest()[:4]
            final_branch_name = f"{raw_branch_name}-v{suffix_hash}"

        return BranchPlan(
            branch_name=final_branch_name,
            base_branch=base_branch,
            purpose=f"Isolated feature branch for {category} {short_id}",
        )

    @staticmethod
    def validate_branch_name(branch_name: str) -> tuple[bool, str | None]:
        """Verify branch name safety constraints."""
        if not branch_name:
            return False, "Branch name is empty."

        if len(branch_name) > 100:
            return False, f"Branch name length {len(branch_name)} exceeds maximum 100 characters."

        if branch_name.startswith("-") or branch_name.startswith("/"):
            return False, f"Branch name cannot start with '-' or '/': '{branch_name}'"

        if ".." in branch_name or "@{" in branch_name or "\\" in branch_name:
            return False, f"Forbidden git path sequence in branch name: '{branch_name}'"

        if not BranchManager.SAFE_BRANCH_PATTERN.match(branch_name):
            return False, f"Branch name contains invalid or unsafe characters: '{branch_name}'"

        return True, None


class FakeBranchManager(BranchManager):
    """Deterministic mock branch manager for testing."""

    pass

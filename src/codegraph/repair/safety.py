"""Repair safety validator enforcing path, bounds, and operation restrictions."""

from codegraph.change.models import Patch, FORBIDDEN_OPERATIONS
from codegraph.change.safety import SafetyValidator
from codegraph.repair.models import RepairPlan


class RepairSafetyValidator:
    """Validates security, path bounds, and operation safety for repair plans and patches."""

    FORBIDDEN_KEYWORDS: set[str] = {
        "git commit",
        "git push",
        "rm -rf",
        "drop table",
        "delete from",
        "subprocess",
        "os.system",
        "eval(",
        "exec(",
        "chmod",
        "chown",
    }

    @staticmethod
    def validate_plan_safety(plan: RepairPlan) -> tuple[bool, str | None]:
        """Verify plan does not attempt forbidden shell or system operations."""
        for op in plan.modifications:
            # 1. Path safety check
            path_ok, path_err = SafetyValidator.validate_path(op.file)
            if not path_ok:
                return False, f"Path security violation in operation for '{op.file}': {path_err}"

            # 2. Forbidden operation check
            if op.operation_type in FORBIDDEN_OPERATIONS or str(op.operation_type) in FORBIDDEN_OPERATIONS:
                return False, f"Forbidden operation type '{op.operation_type}' in repair plan."

            # 3. Forbidden command keyword check
            content_low = f"{op.description} {op.new_code}".lower()
            for kw in RepairSafetyValidator.FORBIDDEN_KEYWORDS:
                if kw in content_low:
                    return False, f"Security violation: forbidden keyword '{kw}' detected in repair plan."

        return True, None

    @staticmethod
    def validate_patch_safety(patch: Patch) -> tuple[bool, str | None]:
        """Delegate to Phase 8 SafetyValidator for path safety and bounds clamping."""
        for fc in patch.file_changes:
            safe, err = SafetyValidator.validate_path(fc.file_path)
            if not safe:
                return False, err
        return SafetyValidator.validate_patch_bounds(len(patch.files), patch.lines_added + patch.lines_removed)

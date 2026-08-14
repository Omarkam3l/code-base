"""Patch generator for Phase 8 Code Change Planning & Patch Generation."""

from typing import Any
from codegraph.change.models import (
    ChangePlan,
    Patch,
    PatchFileChange,
    ChangeOperationType,
)
from codegraph.change.diff import UnifiedDiffBuilder
from codegraph.change.safety import SafetyValidator, MAX_FILES_DEFAULT, MAX_CHANGED_LINES_DEFAULT


class PatchGenerator:
    """Generates structured unified diff patches from validated ChangePlans."""

    def __init__(
        self,
        max_files: int = MAX_FILES_DEFAULT,
        max_lines: int = MAX_CHANGED_LINES_DEFAULT,
    ) -> None:
        self.max_files = max_files
        self.max_lines = max_lines

    def generate_patch(
        self,
        plan: ChangePlan,
        source_code_map: dict[str, str],
    ) -> tuple[Patch | None, str | None]:
        """Generate unified diff Patch from plan and current source code map.

        Returns (patch, error_reason).
        """
        if not plan.is_valid:
            return None, f"Cannot generate patch for invalid plan: {plan.rejection_reason}"

        file_changes: list[PatchFileChange] = []
        full_diff_parts: list[str] = []
        total_added = 0
        total_removed = 0
        touched_files: list[str] = []

        for op in plan.modifications:
            file_path = op.file
            # Path safety check
            valid_path, reason = SafetyValidator.validate_path(file_path)
            if not valid_path:
                return None, f"Unsafe file path in patch operation: {reason}"

            old_content = source_code_map.get(file_path, "")
            new_content = op.new_code if op.new_code else old_content

            diff_text = UnifiedDiffBuilder.generate_diff(file_path, old_content, new_content)
            added, removed = UnifiedDiffBuilder.count_diff_lines(diff_text)

            total_added += added
            total_removed += removed

            file_changes.append(
                PatchFileChange(
                    file_path=file_path,
                    operation_type=op.operation_type if isinstance(op.operation_type, ChangeOperationType) else ChangeOperationType.MODIFY_FUNCTION,
                    old_content=old_content,
                    new_content=new_content,
                    diff_snippet=diff_text,
                )
            )
            full_diff_parts.append(diff_text)
            if file_path not in touched_files:
                touched_files.append(file_path)

        total_lines_changed = total_added + total_removed

        # Validate patch bounds
        valid_bounds, bound_reason = SafetyValidator.validate_patch_bounds(
            file_count=len(touched_files),
            lines_changed=total_lines_changed,
            max_files=self.max_files,
            max_lines=self.max_lines,
        )
        if not valid_bounds:
            return None, bound_reason

        unified_diff = "\n".join(full_diff_parts)

        patch = Patch(
            files=tuple(touched_files),
            unified_diff=unified_diff,
            file_changes=tuple(file_changes),
            metadata={"plan_objective": plan.objective, "root_cause": plan.root_cause},
            lines_added=total_added,
            lines_removed=total_removed,
        )

        return patch, None


class DeterministicPatchGenerator(PatchGenerator):
    """Deterministic patch generator for unit tests and reproducible builds."""

    pass

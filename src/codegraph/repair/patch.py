"""Repair patch generation module reusing Phase 8 patch generation API."""

from codegraph.change.models import ChangePlan, Patch
from codegraph.change.patch import PatchGenerator, DeterministicPatchGenerator
from codegraph.change.safety import SafetyValidator
from codegraph.change.validator import ASTValidator, PatchValidator
from codegraph.repair.models import RepairPlan


class RepairPatchGenerator:
    """Generates repair patches reusing Phase 8 patch generator with strict safety & AST validation."""

    def __init__(self, use_deterministic: bool = True) -> None:
        self.use_deterministic = use_deterministic
        if use_deterministic:
            self.phase8_patch_gen = DeterministicPatchGenerator()
        else:
            self.phase8_patch_gen = PatchGenerator()

    def generate_repair_patch(
        self,
        repair_plan: RepairPlan,
        initial_plan: ChangePlan,
        source_code_map: dict[str, str],
    ) -> tuple[Patch | None, str | None]:
        """Generate unified diff patch for RepairPlan and validate safety & AST syntax."""
        # Convert RepairPlan into ChangePlan structure for Phase 8 generator
        change_plan_view = ChangePlan(
            objective=repair_plan.objective,
            root_cause=repair_plan.diagnosis.root_cause_hypothesis,
            affected_entities=repair_plan.affected_entities,
            affected_files=repair_plan.affected_files,
            modifications=repair_plan.modifications,
            risks=initial_plan.risks,
            validation_strategy=repair_plan.validation_strategy,
            evidence_references=repair_plan.diagnosis.evidence_ids,
            is_valid=repair_plan.is_valid,
        )

        # Call Phase 8 Patch Generator
        patch, patch_err = self.phase8_patch_gen.generate_patch(change_plan_view, source_code_map)
        if patch_err or not patch:
            return None, f"Patch generation error: {patch_err}"

        # 1. Safety Validator (Path safety, bounds clamping)
        for fc in patch.file_changes:
            path_safe, path_err = SafetyValidator.validate_path(fc.file_path)
            if not path_safe:
                return None, f"Patch safety validation failed: {path_err}"

        safe, safety_err = SafetyValidator.validate_patch_bounds(len(patch.files), patch.lines_added + patch.lines_removed)
        if not safe:
            return None, f"Patch safety validation failed: {safety_err}"

        # 2. Scope Check
        initial_files = set(initial_plan.affected_files)
        for f in patch.files:
            if f not in initial_files and not repair_plan.scope_justification:
                return None, f"Repair patch expands scope to '{f}' without justification or evidence."

        # 3. AST Validation
        for fc in patch.file_changes:
            ast_valid, ast_err = ASTValidator.validate_source_code(fc.file_path, fc.new_content)
            if not ast_valid:
                return None, f"AST syntax validation failed for '{fc.file_path}': {ast_err}"

        return patch, None

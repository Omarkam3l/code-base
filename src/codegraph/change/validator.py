"""Patch and AST validation for Phase 8 Code Change Planning & Patch Generation."""

import ast
from codegraph.change.models import Patch, ValidationResult, ChangePlan
from codegraph.change.safety import SafetyValidator
from codegraph.change.diff import UnifiedDiffBuilder


class PatchValidator:
    """Pre-apply validator for unified diffs and plan scope alignment."""

    @staticmethod
    def validate_patch_scope(patch: Patch, plan: ChangePlan) -> tuple[bool, str | None]:
        """Verify patch contains ONLY planned files and operations with no scope drift."""
        planned_files_set = set(plan.affected_files)
        patch_files_set = set(patch.files)

        # Check for unplanned files
        unplanned = patch_files_set - planned_files_set
        if unplanned:
            return False, f"Patch touches unplanned files: {unplanned}"

        # Verify path safety for all patch files
        for f in patch.files:
            valid_path, reason = SafetyValidator.validate_path(f)
            if not valid_path:
                return False, f"Patch path safety violation: {reason}"

        return True, None


class ASTValidator:
    """Post-apply AST validator using Tree-sitter / Python ast module."""

    @staticmethod
    def validate_source_code(file_path: str, source_code: str) -> tuple[bool, str | None]:
        """Verify source code parses without Python syntax errors or AST corruption."""
        if not file_path.endswith(".py"):
            return True, None

        try:
            ast.parse(source_code, filename=file_path)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error in '{file_path}' at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"AST parsing failure in '{file_path}': {e}"

    @staticmethod
    def validate_modified_symbols(
        source_code: str,
        expected_symbol: str,
    ) -> tuple[bool, str | None]:
        """Verify that modified symbol exists in parsed AST."""
        try:
            tree = ast.parse(source_code)
            defined_symbols = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined_symbols.add(node.name)

            if expected_symbol and expected_symbol not in defined_symbols:
                return False, f"Expected symbol '{expected_symbol}' not found in updated AST"

            return True, None
        except Exception as e:
            return False, f"Symbol validation error: {e}"

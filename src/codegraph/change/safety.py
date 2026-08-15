"""Safety validation for Phase 8 Code Change Planning & Patch Generation."""

import os
from pathlib import Path
from codegraph.change.models import ChangeOperationType, FORBIDDEN_OPERATIONS

MAX_FILES_DEFAULT = 10
MAX_CHANGED_LINES_DEFAULT = 300
DEFAULT_TEST_TIMEOUT = 60
MAX_TEST_TIMEOUT = 300

# System directories that should never be registerable as a repository root,
# regardless of allowlist configuration. Checked case-insensitively against
# the *resolved* (symlink-following) path.
SENSITIVE_PATH_PREFIXES: tuple[str, ...] = (
    "/etc", "/root", "/proc", "/sys", "/boot", "/var/run", "/private/etc",
    "c:\\windows", "c:\\users\\administrator",
)


class SafetyValidator:
    """Validator enforcing path safety, operation constraints, and bounds limits."""

    @staticmethod
    def validate_path(file_path: str, repo_root: str | None = None) -> tuple[bool, str | None]:
        """Validate path against path traversal, absolute paths, and escapes."""
        if not file_path:
            return False, "Path is empty"

        # Check path traversal tokens
        if "../" in file_path or "..\\" in file_path or file_path.startswith(".."):
            return False, f"Path traversal attempt detected: '{file_path}'"

        # Check absolute path
        if os.path.isabs(file_path) or file_path.startswith("/") or (len(file_path) > 1 and file_path[1] == ":"):
            return False, f"Absolute paths are forbidden: '{file_path}'"

        # Check null byte / symlink trickery
        if "\0" in file_path:
            return False, f"Null byte in path: '{file_path}'"

        if repo_root:
            abs_root = Path(repo_root).resolve()
            target_path = (abs_root / file_path).resolve()
            try:
                target_path.relative_to(abs_root)
            except ValueError:
                return False, f"Path escapes repository root: '{file_path}'"

        return True, None

    @staticmethod
    def validate_repository_root(path_str: str, allowed_roots: list[str] | None = None) -> tuple[bool, str | None]:
        """Validate an absolute filesystem path being registered as a repository root.

        Unlike validate_path (which validates relative in-repo paths), this checks a
        path a caller wants to *register* as a repository — following symlinks and
        resolving '..' segments so trickery can't escape the check, then requiring
        the resolved path to sit under an explicit allowlist (when provided) and
        never under a small set of sensitive system directories.
        """
        if not path_str:
            return False, "Path is empty"

        if ".." in path_str:
            return False, f"Path traversal rejected: '{path_str}'"

        if "\0" in path_str:
            return False, f"Null byte in path: '{path_str}'"

        try:
            resolved = Path(path_str).resolve(strict=False)
        except (OSError, RuntimeError) as e:
            return False, f"Could not resolve path: {e}"

        resolved_lower = str(resolved).lower()
        for prefix in SENSITIVE_PATH_PREFIXES:
            if resolved_lower.startswith(prefix.lower()):
                return False, f"Registering a system path is forbidden: '{resolved}'"

        if allowed_roots:
            for root in allowed_roots:
                try:
                    abs_root = Path(root).resolve(strict=False)
                    resolved.relative_to(abs_root)
                    return True, None
                except ValueError:
                    continue
            return False, f"Path is outside allowed repository roots: '{resolved}'"

        return True, None

    @staticmethod
    def validate_operation_type(op_type_str: str) -> tuple[bool, str | None]:
        """Check if operation is supported and not forbidden."""
        if op_type_str in FORBIDDEN_OPERATIONS:
            return False, f"Forbidden operation type: '{op_type_str}'"

        try:
            ChangeOperationType(op_type_str)
            return True, None
        except ValueError:
            return False, f"Unsupported operation type: '{op_type_str}'"

    @staticmethod
    def validate_patch_bounds(
        file_count: int,
        lines_changed: int,
        max_files: int = MAX_FILES_DEFAULT,
        max_lines: int = MAX_CHANGED_LINES_DEFAULT,
    ) -> tuple[bool, str | None]:
        """Verify patch file count and line changes do not exceed bounds."""
        if file_count > max_files:
            return False, f"Patch file count {file_count} exceeds maximum allowed ({max_files})"

        if lines_changed > max_lines:
            return False, f"Patch changed lines {lines_changed} exceeds maximum allowed ({max_lines})"

        return True, None

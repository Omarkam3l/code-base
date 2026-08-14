"""Unified diff generation and formatting utilities for Phase 8."""

import difflib


class UnifiedDiffBuilder:
    """Helper for building and parsing unified diffs."""

    @staticmethod
    def generate_diff(file_path: str, old_content: str, new_content: str) -> str:
        """Generate standard unified diff for a single file."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

    @staticmethod
    def count_diff_lines(unified_diff: str) -> tuple[int, int]:
        """Count added (+) and removed (-) lines in unified diff."""
        added = 0
        removed = 0
        for line in unified_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
        return added, removed

    @staticmethod
    def parse_diff_files(unified_diff: str) -> tuple[str, ...]:
        """Extract modified file paths from unified diff headers."""
        files = []
        for line in unified_diff.splitlines():
            if line.startswith("+++ b/"):
                files.append(line[6:].strip())
            elif line.startswith("--- a/"):
                f = line[6:].strip()
                if f not in files and f != "/dev/null":
                    files.append(f)
        return tuple(files)

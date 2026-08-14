"""Repository scanner for discovering Python source files."""

import os
from pathlib import Path
from typing import Sequence

DEFAULT_IGNORE_DIRS: set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def scan_repository(
    root: Path | str,
    ignore_dirs: set[str] | Sequence[str] | None = None,
) -> list[Path]:
    """Recursively scan a repository directory for Python (.py) source files.

    Args:
        root: Root path of the repository to scan.
        ignore_dirs: Set or sequence of directory names to ignore during traversal.
            If None, DEFAULT_IGNORE_DIRS is used.

    Returns:
        A deterministically sorted list of Path objects representing Python files found.
    """
    root_path = Path(root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Root repository path does not exist or is not a directory: {root}")

    ignored = set(ignore_dirs) if ignore_dirs is not None else DEFAULT_IGNORE_DIRS

    python_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        # Modify dirnames in-place to prevent traversing ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignored]

        for filename in filenames:
            if filename.endswith(".py"):
                file_path = Path(dirpath) / filename
                if file_path.is_file():
                    python_files.append(file_path)

    # Sort deterministically by relative path string with POSIX separators
    python_files.sort(key=lambda p: p.relative_to(root_path).as_posix())
    return python_files

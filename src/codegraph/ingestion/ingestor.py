"""High-level repository ingestor API orchestrating scanner, parser, and extractor."""

from pathlib import Path
from typing import Sequence

from codegraph.domain.entities import PythonFile, Repository
from codegraph.ingestion.extractor import PythonExtractor
from codegraph.ingestion.parser import PythonParser
from codegraph.ingestion.scanner import scan_repository


def compute_module_name(rel_path: Path) -> str:
    """Deterministically compute Python module name relative to repository root.

    Rules:
        - `app/services/user.py` -> `app.services.user`
        - `app/services/__init__.py` -> `app.services`
        - `__init__.py` -> `__init__`
        - `main.py` -> `main`
    """
    parts = list(rel_path.parts)
    if not parts:
        return ""

    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    if parts[-1] == "__init__":
        parts.pop()
        if not parts:
            return "__init__"

    return ".".join(parts)


class RepositoryIngestor:
    """Orchestrates Phase 1 Repository Ingestion pipeline.

    Scanner -> Parser -> Extractor -> Domain Entities.
    """

    def __init__(
        self,
        root: Path | str,
        ignore_dirs: set[str] | Sequence[str] | None = None,
        parser: PythonParser | None = None,
        extractor: PythonExtractor | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.ignore_dirs = set(ignore_dirs) if ignore_dirs is not None else None
        self.parser = parser or PythonParser()
        self.extractor = extractor or PythonExtractor()

    def ingest(self) -> Repository:
        """Scan, parse, and extract Python repository entities into a Repository object.

        Returns:
            Repository domain entity containing all parsed PythonFiles and failed files.
        """
        if not self.root.exists() or not self.root.is_dir():
            raise ValueError(f"Repository root does not exist or is not a directory: {self.root}")

        scanned_paths = scan_repository(self.root, ignore_dirs=self.ignore_dirs)
        parsed_files: list[PythonFile] = []
        failed_files: list[str] = []

        for file_path in scanned_paths:
            rel_path = file_path.relative_to(self.root)
            posix_path = rel_path.as_posix()
            module_name = compute_module_name(rel_path)

            try:
                source_bytes = file_path.read_bytes()
            except Exception as e:
                failed_files.append(posix_path)
                continue

            try:
                parse_result = self.parser.parse(source_bytes)
                py_file = self.extractor.extract(
                    parse_result=parse_result,
                    path=posix_path,
                    module_name=module_name,
                )
                parsed_files.append(py_file)

                if py_file.has_syntax_errors:
                    failed_files.append(posix_path)

            except Exception:
                failed_files.append(posix_path)

        # Sort results deterministically by relative path
        parsed_files.sort(key=lambda f: f.path)
        failed_files.sort()

        # Remove duplicates from failed_files while keeping sorted order
        unique_failed = sorted(set(failed_files))

        return Repository(
            root_path=str(self.root),
            files=tuple(parsed_files),
            failed_files=tuple(unique_failed),
        )

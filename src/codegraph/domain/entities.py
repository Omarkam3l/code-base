"""Domain entities representing Python code elements and repositories.

All entities are immutable and enforce deterministic collections (tuples).
SourceLocation uses 0-based indexing for line and column numbers matching Tree-sitter AST ranges.
"""

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Represents a location in a source file using 0-based line and column indexing."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class Parameter:
    """Represents a function or method parameter."""

    name: str
    type_annotation: str | None = None
    default_value: str | None = None
    kind: str = "POSITIONAL_OR_KEYWORD"


@dataclass(frozen=True, slots=True)
class Import:
    """Represents an import statement in a Python file.

    Examples:
        - `import os` -> module="os", name="", alias=None
        - `import os.path as path_mod` -> module="os.path", name="", alias="path_mod"
        - `from app.database import Database as DB` -> module="app.database", name="Database", alias="DB"
        - `from .models import User` -> module="models", name="User", alias=None, is_relative=True, level=1
    """

    module: str | None = None
    name: str = ""
    alias: str | None = None
    is_relative: bool = False
    level: int = 0
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Function:
    """Represents a top-level function or class method."""

    name: str
    location: SourceLocation
    parameters: tuple[Parameter, ...] = field(default_factory=tuple)
    return_annotation: str | None = None
    is_async: bool = False
    docstring: str | None = None


@dataclass(frozen=True, slots=True)
class Class:
    """Represents a Python class."""

    name: str
    location: SourceLocation
    methods: tuple[Function, ...] = field(default_factory=tuple)
    docstring: str | None = None


@dataclass(frozen=True, slots=True)
class PythonFile:
    """Represents a Python source file in a repository."""

    path: str  # Repository-relative path with forward slashes (e.g., "app/services/user.py")
    module_name: str  # Deterministically calculated module name (e.g., "app.services.user")
    imports: tuple[Import, ...] = field(default_factory=tuple)
    classes: tuple[Class, ...] = field(default_factory=tuple)
    functions: tuple[Function, ...] = field(default_factory=tuple)
    has_syntax_errors: bool = False
    syntax_errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Repository:
    """Represents an ingested Python repository."""

    root_path: str
    files: tuple[PythonFile, ...] = field(default_factory=tuple)
    failed_files: tuple[str, ...] = field(default_factory=tuple)

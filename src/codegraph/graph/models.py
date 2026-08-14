"""Graph entity models and deterministic identity generators for Code Knowledge Graph."""

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping


def make_repository_id(name_or_path: str) -> str:
    """Generate deterministic repository ID."""
    clean = Path(name_or_path).as_posix().strip("/").lower()
    # Use basename if full path
    name = Path(clean).name or clean
    return f"repository:{name}"


def make_file_id(relative_path: str) -> str:
    """Generate deterministic file ID."""
    clean = Path(relative_path).as_posix().lstrip("./")
    return f"file:{clean}"


def make_module_id(module_name: str) -> str:
    """Generate deterministic module ID."""
    return f"module:{module_name}"


def make_class_id(module_name: str, qualified_name: str) -> str:
    """Generate deterministic class ID."""
    return f"class:{module_name}:{qualified_name}"


def make_function_id(module_name: str, qualified_name: str) -> str:
    """Generate deterministic function ID."""
    return f"function:{module_name}:{qualified_name}"


def make_method_id(module_name: str, class_name: str, method_name: str) -> str:
    """Generate deterministic method ID."""
    return f"method:{module_name}:{class_name}:{method_name}"


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Base class for Neo4j graph nodes."""

    id: str
    labels: tuple[str, ...]

    def to_properties(self) -> dict[str, Any]:
        """Convert node attributes to dictionary for Cypher query parameters."""
        props = {}
        for f in fields(self):
            if f.name != "labels":
                v = getattr(self, f.name)
                if v is not None:
                    props[f.name] = v
        return props


@dataclass(frozen=True, slots=True)
class RepositoryNode(GraphNode):
    name: str = ""
    root_path: str = ""


@dataclass(frozen=True, slots=True)
class FileNode(GraphNode):
    path: str = ""
    language: str = "python"
    module_name: str = ""


@dataclass(frozen=True, slots=True)
class ModuleNode(GraphNode):
    name: str = ""


@dataclass(frozen=True, slots=True)
class ClassNode(GraphNode):
    name: str = ""
    qualified_name: str = ""
    file_path: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    docstring: str | None = None


@dataclass(frozen=True, slots=True)
class FunctionNode(GraphNode):
    name: str = ""
    qualified_name: str = ""
    file_path: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    return_annotation: str | None = None
    docstring: str | None = None


@dataclass(frozen=True, slots=True)
class MethodNode(GraphNode):
    name: str = ""
    qualified_name: str = ""
    file_path: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    return_annotation: str | None = None
    docstring: str | None = None


@dataclass(frozen=True, slots=True)
class GraphRelationship:
    """Represents a directional relationship between two graph nodes."""

    source_id: str
    relationship_type: str
    target_id: str
    properties: dict[str, Any] = field(default_factory=dict)

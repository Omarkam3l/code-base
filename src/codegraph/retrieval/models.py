"""Domain models for code chunking, vector/graph retrieval, RRF fusion, and context building."""

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """Represents a searchable code snippet extracted from a Phase 1 domain entity."""

    id: str
    entity_id: str
    repository_id: str
    file_path: str
    module_name: str
    entity_type: str  # "class", "function", "method"
    name: str
    qualified_name: str
    source_code: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Result returned by vector retrieval."""

    chunk_id: str
    entity_id: str
    score: float
    rank: int
    source: str = "vector"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphResult:
    """Result returned by structural graph retrieval."""

    entity_id: str
    score: float
    rank: int
    relationship_path: tuple[str, ...] = field(default_factory=tuple)
    source: str = "graph"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FusedResult:
    """Result after Reciprocal Rank Fusion (RRF) deduplication and ranking."""

    chunk_id: str
    entity_id: str
    score: float
    vector_rank: int | None = None
    graph_rank: int | None = None
    vector_score: float | None = None
    graph_score: float | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContextItem:
    """Structured context item for downstream Phase 4 LLM usage."""

    entity_id: str
    file_path: str
    qualified_name: str
    start_line: int
    end_line: int
    retrieved_by: tuple[str, ...]
    score: float
    source_code: str

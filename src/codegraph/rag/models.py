"""Domain models for Graph-RAG reasoning, evidence graphs, and grounded answers."""

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class UserQuery:
    """User query container."""

    query: str
    repository_id: str


@dataclass(frozen=True, slots=True)
class QueryIntent:
    """Structured query intent extracted by QueryAnalyzer."""

    intent_type: str  # "symbol_lookup", "call_flow", "dependency", "architecture", "inheritance", "implementation", "explanation", "debugging"
    entities: tuple[str, ...] = field(default_factory=tuple)
    concepts: tuple[str, ...] = field(default_factory=tuple)
    requested_relationships: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    """Bounded plan for hybrid retrieval and graph context expansion."""

    vector_top_k: int = 10
    graph_top_k: int = 10
    graph_depth: int = 1
    max_context_items: int = 15
    relationship_types: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Evidence:
    """Individual provenance-grounded code evidence item with a citation ID."""

    citation_id: str  # "E1", "E2", etc.
    entity_id: str
    entity_type: str  # "class", "function", "method", "file"
    qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    source_code: str
    retrieval_source: tuple[str, ...] = field(default_factory=tuple)  # ("vector", "graph")
    retrieval_score: float = 0.0
    graph_distance: int = 0
    relationships: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EvidenceGraph:
    """Structured evidence graph payload preserving nodes, edges, and provenance."""

    nodes: tuple[Evidence, ...] = field(default_factory=tuple)
    edges: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Answer:
    """Grounded RAG answer output with citation validation metadata."""

    text: str
    citations: tuple[str, ...] = field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    confidence: str = "medium"  # "high", "medium", "low"
    insufficient_evidence: bool = False
    validation_passed: bool = True
    validation_errors: tuple[str, ...] = field(default_factory=tuple)

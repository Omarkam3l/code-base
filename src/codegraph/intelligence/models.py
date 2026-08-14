"""Domain models for structural Code Intelligence and multi-hop reasoning."""

from dataclasses import dataclass, field
from typing import Any
from codegraph.intelligence.query_types import IntelligenceQueryType
from codegraph.rag.models import Answer, EvidenceGraph


@dataclass(frozen=True)
class IntelligenceQuery:
    """Natural language query enriched with identified intelligence query type and target entities."""

    query: str
    repository_id: str
    query_type: IntelligenceQueryType
    target_entities: tuple[str, ...] = ()
    source_entity: str | None = None
    target_entity: str | None = None


@dataclass(frozen=True)
class IntelligencePlan:
    """Bounded plan specifying graph traversal parameters and limits."""

    max_depth: int = 4
    max_paths: int = 10
    max_nodes: int = 100
    relationship_types: tuple[str, ...] = ("CALLS", "IMPORTS", "INHERITS")
    direction: str = "outgoing"  # outgoing, incoming, both

    def __post_init__(self) -> None:
        # Enforce hard limits
        if self.max_depth > 8:
            object.__setattr__(self, "max_depth", 8)
        if self.max_paths > 50:
            object.__setattr__(self, "max_paths", 50)
        if self.max_nodes > 500:
            object.__setattr__(self, "max_nodes", 500)


@dataclass(frozen=True)
class PathResult:
    """Structured result of a single multi-hop graph path traversal."""

    nodes: tuple[dict[str, Any], ...]
    relationships: tuple[dict[str, Any], ...]
    total_cost: float
    depth: int
    path_id: str = ""

    def __post_init__(self) -> None:
        if not self.path_id and self.nodes:
            n_ids = tuple(n.get("id", str(idx)) for idx, n in enumerate(self.nodes))
            object.__setattr__(self, "path_id", "->".join(n_ids))


@dataclass(frozen=True)
class ImpactResult:
    """Structured change-impact analysis result distinguishing direct vs transitive dependents."""

    target: str
    direct_dependents: tuple[dict[str, Any], ...]
    indirect_dependents: tuple[dict[str, Any], ...]
    affected_files: tuple[str, ...]
    affected_modules: tuple[str, ...]


@dataclass(frozen=True)
class DependencyResult:
    """Structured dependency result broken down by relationship type."""

    entity: str
    dependencies: tuple[dict[str, Any], ...]  # Outgoing (IMPORTS, CALLS, INHERITS)
    dependents: tuple[dict[str, Any], ...]    # Incoming (imported by, called by, inherited by)


@dataclass(frozen=True)
class ArchitectureFlow:
    """Discovered architectural layers and component flow in the repository."""

    entry_points: tuple[dict[str, Any], ...]
    intermediate_components: tuple[dict[str, Any], ...]
    persistence_components: tuple[dict[str, Any], ...]
    external_boundaries: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class IntelligenceResult:
    """Final unified result of a Code Intelligence execution."""

    query: IntelligenceQuery
    plan: IntelligencePlan
    paths: tuple[PathResult, ...] = ()
    impact: ImpactResult | None = None
    dependency: DependencyResult | None = None
    architecture: ArchitectureFlow | None = None
    evidence_graph: EvidenceGraph = field(default_factory=EvidenceGraph)
    answer: Answer | None = None
    execution_time_ms: float = 0.0

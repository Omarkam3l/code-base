"""Repository size fixtures and deterministic fault injection harness for Phase 12."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RepositoryFixture:
    """Fixture metadata representing a deterministic synthetic repository profile."""

    name: str
    file_count: int
    architecture: str  # small, medium, large, layered, monorepo, circular
    root_path: Path


class FaultInjector:
    """Deterministic fault injection harness simulating component failures."""

    def __init__(self) -> None:
        self.active_faults: set[str] = set()

    def inject_fault(self, fault_type: str) -> None:
        """Inject simulated failure mode (neo4j_down, chroma_down, timeout, github_down)."""
        self.active_faults.add(fault_type)

    def clear_faults(self) -> None:
        """Clear all active injected faults."""
        self.active_faults.clear()

    def is_fault_active(self, fault_type: str) -> bool:
        """Check if a specific fault type is active."""
        return fault_type in self.active_faults

"""Tracing span model for Phase 12 Observability."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    """Represents a single executable operation span within a trace."""

    trace_id: str
    span_id: str
    parent_span_id: str | None
    component: str
    operation: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "OK"  # OK, ERROR, ABSTAIN
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "OK", error: str | None = None) -> None:
        """Mark span execution completion and calculate duration."""
        import time

        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.status = status
        self.error = error

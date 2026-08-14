"""TraceManager orchestrating spans and execution traces for Phase 12 Observability."""

import time
import uuid
from typing import Any
from codegraph.observability.correlation import CorrelationContext
from codegraph.observability.redaction import SecretRedactor
from codegraph.observability.spans import Span


class TraceManager:
    """Manages system-wide execution traces, active spans, and correlation context."""

    def __init__(self, context: CorrelationContext | None = None) -> None:
        self.context = context or CorrelationContext.create()
        self.spans: list[Span] = []
        self._active_spans: dict[str, Span] = {}

    def start_span(
        self,
        component: str,
        operation: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Span:
        """Start a new operation span associated with the trace."""
        span_id = f"sp_{uuid.uuid4().hex[:8]}"
        clean_meta = SecretRedactor.redact_object(metadata or {})

        span = Span(
            trace_id=self.context.trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            component=component,
            operation=operation,
            start_time=time.perf_counter(),
            metadata=clean_meta,
        )
        self.spans.append(span)
        self._active_spans[span_id] = span
        return span

    def finish_span(
        self,
        span: Span,
        status: str = "OK",
        error: str | None = None,
        metadata_update: dict[str, Any] | None = None,
    ) -> None:
        """Finish a span and record duration."""
        clean_err = SecretRedactor.redact_text(error) if error else None
        if metadata_update:
            span.metadata.update(SecretRedactor.redact_object(metadata_update))

        span.finish(status=status, error=clean_err)
        if span.span_id in self._active_spans:
            del self._active_spans[span.span_id]

    def get_summary(self) -> dict[str, Any]:
        """Return a structured summary of trace execution."""
        total_duration = sum(s.duration_ms for s in self.spans)
        component_durations: dict[str, float] = {}

        for s in self.spans:
            component_durations[s.component] = component_durations.get(s.component, 0.0) + s.duration_ms

        return {
            "trace_id": self.context.trace_id,
            "repository_id": self.context.repository_id,
            "commit_sha": self.context.commit_sha,
            "branch": self.context.branch,
            "total_spans": len(self.spans),
            "total_duration_ms": total_duration,
            "component_durations": component_durations,
            "status": "ERROR" if any(s.status == "ERROR" for s in self.spans) else "OK",
        }

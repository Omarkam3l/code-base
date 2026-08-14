"""Unit tests for Phase 12 Observability (Span, TraceManager, SecretRedactor, CorrelationContext)."""

from codegraph.observability.correlation import CorrelationContext
from codegraph.observability.events import EventLogger
from codegraph.observability.metrics import MetricsCollector
from codegraph.observability.redaction import SecretRedactor
from codegraph.observability.traces import TraceManager


def test_secret_redactor_masks_credentials() -> None:
    text = "Authorization token: ghp_1234567890abcdef1234567890abcdef1234 and AWS_KEY: AKIAIOSFODNN7EXAMPLE"
    redacted = SecretRedactor.redact_text(text)

    assert "ghp_1234567890abcdef1234567890abcdef1234" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED" in redacted


def test_trace_manager_span_lifecycle() -> None:
    context = CorrelationContext.create(repository_id="repository:sample_project")
    manager = TraceManager(context=context)

    span = manager.start_span(component="retrieval", operation="hybrid_search", metadata={"query": "UserService"})
    assert span.trace_id == context.trace_id
    assert span.component == "retrieval"

    manager.finish_span(span, status="OK")
    assert span.duration_ms >= 0.0

    summary = manager.get_summary()
    assert summary["total_spans"] == 1
    assert "retrieval" in summary["component_durations"]


def test_event_logger_and_metrics_collector() -> None:
    logger = EventLogger(component_name="repair")
    evt = logger.log_event("repair_iteration", level="INFO", details={"patch": "valid"})

    assert evt["component"] == "repair"
    assert evt["event"] == "repair_iteration"

    metrics = MetricsCollector()
    metrics.record_latency(150.0)
    metrics.record_latency(250.0)
    stats = metrics.get_latency_stats()

    assert stats["p50"] == 200.0
    assert stats["avg"] == 200.0

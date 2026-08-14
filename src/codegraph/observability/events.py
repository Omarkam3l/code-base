"""Structured EventLogger for Phase 12 Observability."""

import time
from typing import Any
from codegraph.observability.redaction import SecretRedactor


class EventLogger:
    """Structured event logging with secret redaction and correlation IDs."""

    def __init__(self, component_name: str = "codegraph") -> None:
        self.component_name = component_name
        self.events: list[dict[str, Any]] = []

    def log_event(
        self,
        event_name: str,
        level: str = "INFO",
        trace_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a structured event record."""
        clean_details = SecretRedactor.redact_object(details or {})
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level.upper(),
            "component": self.component_name,
            "event": event_name,
            "trace_id": trace_id or "untraced",
            "details": clean_details,
        }
        self.events.append(record)
        return record

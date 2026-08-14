"""TraceExporter exporting execution traces to JSON/JSONL format."""

import json
from pathlib import Path
from typing import Sequence
from codegraph.observability.redaction import SecretRedactor
from codegraph.observability.traces import TraceManager


class TraceExporter:
    """Exports trace summaries and span records to machine-readable JSON files."""

    @staticmethod
    def export_to_json(manager: TraceManager, output_path: str | Path) -> None:
        """Export full trace record to JSON file with secret redaction."""
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        summary = manager.get_summary()
        spans_data = [
            {
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "component": s.component,
                "operation": s.operation,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "error": s.error,
                "metadata": s.metadata,
            }
            for s in manager.spans
        ]

        payload = {
            "summary": summary,
            "spans": spans_data,
        }
        clean_payload = SecretRedactor.redact_object(payload)
        target_path.write_text(json.dumps(clean_payload, indent=2), encoding="utf-8")

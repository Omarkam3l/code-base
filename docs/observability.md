# CodeGraph RAG — Observability & Unified Tracing Architecture

## 1. Tracing Model
The observability framework (`src/codegraph/observability/`) implements system-wide execution tracing via `TraceManager` and `Span`.

### Correlation Identifiers
- `trace_id`: Unique identifier across an execution trace.
- `repository_id`: Repository identifier.
- `commit_sha`: Active commit SHA.
- `pull_request_id`: Associated PR ID.
- `investigation_id` & `repair_id`: Autonomous investigation and repair loop identifiers.

---

## 2. Span Lifecycle
Every pipeline operation (ingestion, retrieval, graph traversal, change planning, patch repair, git workflow, github integration) emits a `Span` with start/end timestamps, duration, status, and redacted metadata.

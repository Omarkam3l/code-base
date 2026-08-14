# Operations & Production Runbook

## Health Probes
- `GET /health`: Basic service health.
- `GET /live`: Liveness probe.
- `GET /ready`: Readiness probe verifying Neo4j and vector store connectivity.
- `GET /metrics`: Infrastructure metrics.

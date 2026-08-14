# CodeGraph REST API Reference

## Endpoints

- `POST /repositories`: Register repository path.
- `GET /repositories`: List registered repositories.
- `GET /repositories/{id}`: Get repository details.
- `POST /repositories/{id}/index`: Trigger incremental re-indexing.
- `POST /query`: Execute code search query.
- `POST /investigate`: Run autonomous investigation.
- `POST /impact`: Analyze symbol impact.
- `POST /dependencies`: Analyze symbol dependencies.
- `POST /trace`: Trace call flow.
- `POST /changes/plan`: Plan code change.
- `POST /changes/patch`: Generate diff patch.
- `POST /repairs`: Execute iterative repair.
- `GET /traces/{trace_id}`: View trace details.
- `GET /evaluations/latest`: Get latest benchmark report.
- `GET /health`: Health check.

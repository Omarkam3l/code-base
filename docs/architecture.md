# CodeGraph RAG — System Architecture (Phases 1–14)

## Architecture Overview

```text
               Developer CLI / FastAPI REST API / MCP Server
                                    │
                                    ▼
                          PlatformService
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ↓                               ↓                               ↓
ExecutionBackend              JobQueue & Worker              PlatformStore
(Local / Worker)             (Async Job Processing)       (PostgreSQL Metadata)
    │                               │                               │
    └───────────────────────────────┼───────────────────────────────┘
                                    ↓
                       Existing CodeGraph Engine
                      (Phases 1–13 Hardened Core)
```

- **Neo4j**: Code relationship knowledge graph.
- **PostgreSQL**: Platform metadata (`users`, `organizations`, `repositories`, `jobs`).
- **Redis**: Asynchronous job queue broker.
- **Chroma**: Hybrid vector store embeddings.

# Documentation & Diagram Drift Detection

## Consistency Analysis

`ConsistencyAnalyzer` compares documented and diagrammed relationships against actual Neo4j code graph edges.

### Drift Categories

- `MATCH`: Documentation/diagram matches code implementation.
- `CONFLICT`: Documented dependency contradicts actual code (e.g., diagram says Redis, but code uses PostgreSQL).
- `MISSING_IN_CODE`: Documented component or connection has no implementation in code.
- `MISSING_IN_DOCUMENTATION`: Code component has no mention in documentation.
- `UNRESOLVED`: Mapping could not be definitively resolved.

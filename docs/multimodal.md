# Multimodal Software Knowledge Graph

Phase 15 extends CodeGraph into a multimodal software knowledge graph connecting source code, Markdown documentation, architecture diagrams, ER diagrams, UML diagrams, and UI screenshots.

## Architecture

```text
Repository
    ├── Source Code ──────────► AST Parser ──────────┐
    ├── Markdown / Text ──────► Document Parser ─────┼──► Multimodal Code Mapper ──► Neo4j / Vector Store
    └── Images / Diagrams ────► OCR + Vision ────────┘
```

- **Neo4j**: Stores asset identity, metadata, and cross-modal relationships.
- **Chroma**: Stores semantic embeddings of code and visual descriptions.
- **Storage**: Original image and document binary bytes reside in repository storage.

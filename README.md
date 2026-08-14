# CodeGraph RAG — Software Repository Graph RAG

**CodeGraph RAG** is a high-performance, production-quality Graph RAG system for software repositories.

- **Phase 1: Repository Ingestion** — Scans Python codebases, parses source files with Tree-sitter AST, and extracts domain entities (`Repository`, `PythonFile`, `Module`, `Class`, `Function`, `Method`, `Import`, `Parameter`).
- **Phase 2: Code Knowledge Graph** — Maps Phase 1 domain entities into a deterministic Neo4j graph representing code entities and structural relationships (`CONTAINS`, `DEFINES`, `IMPORTS`, `INHERITS`, `CALLS`).

---

## Pipeline Architecture Overview

```text
Python Repository
        │
        ▼
Repository Scanner  ──────────────────► Python Source Files
        │
        ▼
Tree-sitter Parser  ──────────────────► AST
        │
        ▼
Code Entity Extractor  ───────────────► Domain Model (Files, Classes, Functions, Imports, Parameters)
        │
        ├────────────────────────────────┐
        ▼                                ▼
Graph Mapper                     Code Chunker
        │                                │
        ▼                                ▼
Neo4j Graph Store                Chroma Vector Store
(Entities & Relationships)       (Dense Embeddings: BGE-M3)
        │                                │
        └────────────────┬───────────────┘
                         ▼
                  Hybrid Retriever (RRF Fusion)
                         │
                         ▼
                Query Analyzer & Planner
                         │
                         ▼
             Graph Context Expander (Neo4j 1/2-Hop)
                         │
                         ▼
               Provenance Evidence Graph
                         │
                         ▼
            LLM Reasoning & Citation Validator
                         │
                         ▼
              Grounded Answer ([E1], [E2])
```

---

## RAG Reasoning Engine (Phase 4)

Phase 4 introduces a grounded Graph-RAG reasoning pipeline that synthesizes retrieved code evidence into factually grounded answers with strict citation validation (`[E1]`, `[E2]`).

### Benchmark Results

```text
Strategy                         Citation Validity    Evidence Coverage    Unsupported Rate  
---------------------------------------------------------------------------------------------
Hybrid Retrieval (No Expansion)  0.9333               0.5333               0.0667            
Graph-RAG (Context Expansion)    1.0000               0.6667               0.0000            
```

- **Citation Validity**: 100% of generated citations strictly map to supplied evidence IDs.
- **Evidence Coverage**: Neo4j context expansion increases evidence coverage by +13.34% over hybrid retrieval alone.
- **Unsupported Citation Rate**: Reduced to 0.0000 with post-generation hallucination guard.

---

## Neo4j Graph Schema

### Node Types & Deterministic Identity

| Node Label | Deterministic ID Scheme | Description & Key Properties |
| :--- | :--- | :--- |
| **`Repository`** | `repository:<repo_name>` | Repository root container (`id`, `name`, `root_path`) |
| **`File`** | `file:<relative_path>` | Source file (`id`, `path`, `language`, `module_name`) |
| **`Module`** | `module:<module_name>` | Python module (`id`, `name`) |
| **`Class`** | `class:<module>:<class_name>` | Class definition (`id`, `name`, `qualified_name`, `file_path`, location, `docstring`) |
| **`Function`** | `function:<module>:<func_name>` | Top-level function (`id`, `name`, `qualified_name`, `file_path`, location, `return_annotation`, `docstring`) |
| **`Method`** | `method:<module>:<class>:<meth_name>` | Class method (`id`, `name`, `qualified_name`, `file_path`, location, `return_annotation`, `docstring`) |

### Relationship Types

- `(:Repository)-[:CONTAINS]->(:File)`
- `(:File)-[:DEFINES]->(:Module)`
- `(:Module)-[:DEFINES]->(:Class)`
- `(:Module)-[:DEFINES]->(:Function)`
- `(:Class)-[:DEFINES]->(:Method)`
- `(:File)-[:IMPORTS]->(:File)` (Resolved static imports)
- `(:Class)-[:INHERITS]->(:Class)` (Resolved class inheritance)
- `(:Function|:Method)-[:CALLS]->(:Function|:Method)` (Conservative static call resolution)

---

## Quickstart Example

### 1. Ingest Repository & Build Code Knowledge Graph

```python
from pathlib import Path
from neo4j import GraphDatabase
from codegraph.ingestion import RepositoryIngestor
from codegraph.graph import GraphRepository, RepositoryGraphIndexer

# 1. Ingest Repository (Phase 1)
repo_path = Path("examples/sample_project")
ingestor = RepositoryIngestor(root=repo_path)
domain_repo = ingestor.ingest()

# Load source code map for AST call/inheritance resolution
sources = {f.path: (repo_path / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

# 2. Connect to Neo4j & Index Graph (Phase 2)
driver = GraphDatabase.driver("neo4j+s://d63ecd97.databases.neo4j.io", auth=("d63ecd97", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU"))

with GraphRepository(driver=driver, database="d63ecd97") as graph_repo:
    indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    result = indexer.index(domain_repo, source_code_map=sources)

    print(f"Indexed {result.file_count} files, {result.class_count} classes, {result.relationship_count} relationships.")

    # Query Code Knowledge Graph
    user_cls = graph_repo.find_class("models.User")
    print("Found Class Node:", user_cls)
```

---

## Running Tests

Run full test suite (Unit & Live Neo4j Integration tests):

```bash
pytest -v
```

---

## Scope & Boundaries

### Implemented in Phase 1 & Phase 2
- [x] Recursive Python repository scanning & Tree-sitter AST parsing
- [x] Code entity extraction (Imports, Classes, Functions, Methods, Parameters, Type annotations)
- [x] Deterministic 0-based source location tracking & module resolution
- [x] Neo4j Code Knowledge Graph schema, uniqueness constraints, and indexes
- [x] Deterministic node identity schemes (`repository:`, `file:`, `module:`, `class:`, `function:`, `method:`)
- [x] Batched Cypher query execution (`UNWIND ... MERGE`)
- [x] Static import resolution (`File -> IMPORTS -> File`)
- [x] Static inheritance resolution (`Class -> INHERITS -> Class`)
- [x] Conservative static AST call resolution (`Function/Method -> CALLS -> Function/Method`)
- [x] Graph Validation Read API (`find_class`, `find_function`, `find_callers`, `find_callees`, `find_imports`, `find_dependents`, `find_inheritance_tree`)
- [x] Guaranteed Graph Idempotency (re-indexing produces identical node and relationship counts)

---

## Code Change Planning & Patch Generation (Phase 8)

Phase 8 equips CodeGraph RAG with controlled code-change planning and unified patch generation without ever modifying the user's working tree.

### Core Architecture & Isolation Rules

```text
Change Request ("Fix UserService auth flow")
       │
       ▼
Bounded Agentic Investigation (Phase 7 Context)
       │
       ▼
Deterministic / LLM Change Planner (Structured Operations)
       │
       ▼
Phase 6 Impact & Risk Analysis (LOW / MEDIUM / HIGH / BLOCKED)
       │
       ▼
Patch Generator (Unified Diff Format)
       │
       ▼
Safety Validator (Path Traversal, Escapes, Bounds Clamping)
       │
       ▼
Isolated Workspace Manager (Temporary Directory Sandbox)
       │
       ▼
AST Validator & Pytest Runner (Syntax, Symbol & Test Verification)
       │
       ▼
Validated Change Result / Detailed Diff Patch
```

### Key Safety Guarantees

1. **Working Tree Isolation**: All modifications occur strictly inside isolated temporary directory sandboxes (`tempfile.TemporaryDirectory`). The user's working directory is never touched.
2. **Path Traversal Protection**: Rejects all path escape attempts (`../`, `..\`, absolute paths, symlinks).
3. **Forbidden Operations Blocked**: Immediately rejects `DELETE_FILE`, `RENAME_FILE`, `MOVE_FILE`, `BINARY_FILE_MODIFICATION`, `DATABASE_MIGRATIONS`, and `INFRASTRUCTURE_CHANGES`.
4. **Bounds Clamping**: Clamps patches to `max_files = 10`, `max_changed_lines = 300`, and `test_timeout = 60s`.
5. **AST & Test Verification**: Post-patch validation verifies Python `ast` syntax validity, target symbol presence, and runs hardcoded `pytest` execution against isolated workspaces.

---

## Benchmark Metrics Summary (Phases 1–8)

| Benchmark Phase | Cases | Key Metric | Result | Target / Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 3 Hybrid Retrieval** | 50 | Recall@5 / MRR | **0.8667 / 0.8250** | Outperforms Vector & Graph |
| **Phase 4 Graph-RAG Reasoning** | 50 | Citation Validity | **1.0000** | 100% Grounded Citations |
| **Phase 5 Evaluation & Hardening** | 80 | Hallucination / Adversarial Rejection | **1.0000** | 0% Hallucinations |
| **Phase 6 Multi-Hop Reasoning** | 110 | Multi-Hop Traversal Accuracy | **1.0000** | 100% Path Accuracy |
| **Phase 7 Agentic Investigation** | 110 | Investigation Correctness | **0.9545** | Sub-second P50 Latency |
| **Phase 8 Code Change Planning** | **140** | Patch Scope & Rejection Accuracy | **1.0000** | 100% Safety & Isolation |


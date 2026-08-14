# CodeGraph RAG — Software Repository Graph RAG

**CodeGraph RAG** is a high-performance, production-quality Graph RAG system for software repositories.

- **Phase 1: Repository Ingestion** — Scans Python codebases, parses source files with Tree-sitter AST, and extracts domain entities (`Repository`, `PythonFile`, `Module`, `Class`, `Function`, `Method`, `Import`, `Parameter`).
- **Phase 2: Code Knowledge Graph** — Maps Phase 1 domain entities into a deterministic Neo4j graph representing code entities and structural relationships (`CONTAINS`, `DEFINES`, `IMPORTS`, `INHERITS`, `CALLS`).

---

## Pipeline Architecture

```text
Python Repository
        ↓
Phase 1: Repository Scanner (scanner.py)
        ↓
Phase 1: Tree-sitter Parser (parser.py) & AST Extractor (extractor.py)
        ↓
Phase 1: Domain Model (entities.py)
        ↓
Phase 2: Graph Mapper & Resolver (mapper.py)
        ↓
Phase 2: Neo4j Repository (repository.py)
        ↓
Code Knowledge Graph (Neo4j)
```

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

### Reserved for Phase 3+
```text
Embeddings: not implemented
Vector search: not implemented
LLM calls: not implemented
RAG retrieval: not implemented
FastAPI endpoints: not implemented
Semantic retrieval: not implemented
```

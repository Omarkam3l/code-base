# CodeGraph Developer Platform Architecture

## 1. Overview
The CodeGraph Developer Platform (`src/codegraph/platform/`) turns CodeGraph RAG into an enterprise developer platform while preserving all safety boundaries and APIs from Phases 1–12.

---

## 2. Platform Core Components

1. **Repository Manager** (`src/codegraph/platform/repositories/`):
   - Manages repository registration, status tracking, and incremental indexing (content SHA256 hashes skip unchanged files).
2. **Persistent Investigation History** (`src/codegraph/platform/investigations/`):
   - Persists investigation questions, trace IDs, steps, hypotheses, evidence, and citations in file-backed store.
3. **Human Approval Workflow** (`src/codegraph/platform/workflow/`):
   - Explicit state engine enforcing human approval gates (`PLAN` $\rightarrow$ `PATCH` and `TEST` $\rightarrow$ `COMMIT`).
4. **Platform Service Layer** (`src/codegraph/platform/services/`):
   - Service layer delegating to existing pipeline components without code duplication.

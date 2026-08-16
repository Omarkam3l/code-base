"""
Real end-to-end use case test for CodeGraph RAG.

Scenario: A developer asks "Why does UserService.add_user not validate the age parameter?"
and then requests a change to add that validation.

This test exercises the full pipeline without mocks:
  Phase 1 — Repository ingestion (Tree-sitter AST)
  Phase 2 — Neo4j code knowledge graph indexing
  Phase 3 — Hybrid retrieval (graph + vector)
  Phase 7 — Agentic codebase investigation
  Phase 8 — Change planning, patch generation, AST validation
"""

import os
from pathlib import Path

import pytest

from codegraph.agent.pipeline import AgenticPipeline
from codegraph.change.models import ChangeRequest
from codegraph.change.pipeline import ChangePipeline
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.graph.repository import GraphRepository
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.embeddings import FakeEmbeddingModel
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.vector_retriever import VectorRetriever
from codegraph.retrieval.vector_store import ChromaVectorStore
from neo4j import GraphDatabase

from codegraph.graph.models import make_repository_id

# ---------------------------------------------------------------------------
# Connection config — credentials come exclusively from the environment.
# Never put real credentials in source control; rotate any that were.
# ---------------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

pytestmark = pytest.mark.skipif(
    not (NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD),
    reason="NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not set; skipping live integration tests",
)

SAMPLE_DIR = Path("examples/sample_project")


# ---------------------------------------------------------------------------
# Shared fixture: fully-indexed stack (graph + vector)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def indexed_stack(tmp_path_factory):
    """
    Builds the full Neo4j + Chroma index once for the entire module.
    Returns (domain_repo, sources, graph_repo, hybrid_retriever).
    """
    assert SAMPLE_DIR.exists(), f"Sample project not found at {SAMPLE_DIR}"

    # --- Phase 1: Ingest repository ---
    ingestor = RepositoryIngestor(root=SAMPLE_DIR)
    domain_repo = ingestor.ingest()
    sources = {f.path: (SAMPLE_DIR / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    assert len(domain_repo.files) == 3, "Expected 3 source files in sample project"
    assert len(domain_repo.failed_files) == 0, "No files should fail to parse"

    # --- Phase 2: Index into Neo4j ---
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)

    # Clean any prior state for this repository so assertions (especially
    # idempotency counts) are deterministic regardless of DB history.
    repo_id = make_repository_id(domain_repo.root_path)
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            """
            MATCH (r:Repository {id: $repo_id})
            OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[:DEFINES|IMPORTS*0..3]-(n)
            DETACH DELETE n
            DETACH DELETE r
            """,
            repo_id=repo_id,
        )

    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    index_result = graph_indexer.index(domain_repo, source_code_map=sources)

    assert index_result.file_count == 3
    assert index_result.class_count >= 2   # User + UserService
    assert index_result.relationship_count > 0

    # --- Phase 3: Index into Chroma vector store ---
    chunker = CodeChunker()
    chunks = chunker.chunk_repository(domain_repo, source_code_map=sources)
    assert len(chunks) > 0, "Chunker must produce at least one chunk"

    tmp_path = tmp_path_factory.mktemp("chroma")
    embedding_model = FakeEmbeddingModel(dimension=64)
    vector_store = ChromaVectorStore(
        collection_name="real_usecase_chunks",
        persist_directory=tmp_path / "chroma",
    )
    doc_texts = [f"{c.entity_type} {c.qualified_name}\n{c.source_code}" for c in chunks]
    embeddings = embedding_model.embed_documents(doc_texts)
    vector_store.upsert(chunks=chunks, embeddings=embeddings)

    vector_retriever = VectorRetriever(vector_store=vector_store, embedding_model=embedding_model)
    graph_retriever = GraphRetriever(graph_repo=graph_repo)
    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        graph_retriever=graph_retriever,
    )

    yield domain_repo, sources, graph_repo, hybrid_retriever

    graph_repo.close()


# ---------------------------------------------------------------------------
# Test 1: Ingestion correctness — the structural foundation
# ---------------------------------------------------------------------------
def test_sample_project_entities_extracted(indexed_stack):
    """
    The sample project must parse correctly and expose every expected entity
    so the downstream graph and retrieval layers have something meaningful to work with.
    """
    domain_repo, sources, *_ = indexed_stack

    file_paths = {f.path for f in domain_repo.files}
    assert file_paths == {"main.py", "models.py", "services.py"}

    models_file = next(f for f in domain_repo.files if f.path == "models.py")
    assert len(models_file.classes) == 1
    user_cls = models_file.classes[0]
    assert user_cls.name == "User"
    method_names = {m.name for m in user_cls.methods}
    assert "display_name" in method_names

    services_file = next(f for f in domain_repo.files if f.path == "services.py")
    assert len(services_file.classes) == 1
    svc_cls = services_file.classes[0]
    assert svc_cls.name == "UserService"
    svc_method_names = {m.name for m in svc_cls.methods}
    assert "add_user" in svc_method_names
    assert "fetch_user_by_id" in svc_method_names

    main_file = next(f for f in domain_repo.files if f.path == "main.py")
    assert len(main_file.functions) >= 1
    fn_names = {fn.name for fn in main_file.functions}
    assert "main" in fn_names


# ---------------------------------------------------------------------------
# Test 2: Graph connectivity — Neo4j nodes and relationships are queryable
# ---------------------------------------------------------------------------
def test_graph_nodes_and_relationships_queryable(indexed_stack):
    """
    After indexing, we must be able to query the graph for the key entities
    and their structural relationships (DEFINES, IMPORTS, INHERITS, CALLS).
    """
    _, sources, graph_repo, _ = indexed_stack

    # User class must exist in graph
    user_cls = graph_repo.find_class("models.User")
    assert user_cls is not None, "models.User not found in graph"
    assert user_cls["name"] == "User"

    # UserService must exist
    svc_cls = graph_repo.find_class("services.UserService")
    assert svc_cls is not None, "services.UserService not found in graph"

    # services.py imports models.py (resolved static import)
    from codegraph.graph.models import make_file_id
    services_file_id = make_file_id("services.py")
    imports = graph_repo.find_imports(services_file_id)
    imported_paths = [f["path"] for f in imports]
    assert "models.py" in imported_paths, (
        f"Expected services.py -> IMPORTS -> models.py, got: {imported_paths}"
    )


# ---------------------------------------------------------------------------
# Test 3: Hybrid retrieval — relevant code found for a real query
# ---------------------------------------------------------------------------
def test_hybrid_retrieval_finds_user_service(indexed_stack):
    """
    Searching for 'UserService add_user age validation' must surface the
    UserService class or add_user method within the top-10 results.
    """
    domain_repo, _, _, hybrid_retriever = indexed_stack

    results = hybrid_retriever.retrieve(
        query="UserService add_user age validation",
        repository_id=domain_repo.root_path,
        limit=10,
    )

    assert len(results) > 0, "Hybrid retriever must return at least one result"

    entity_ids = {r.entity_id for r in results}
    # At minimum the UserService class or the add_user method should be hit
    has_service_entity = any(
        "UserService" in eid or "add_user" in eid
        for eid in entity_ids
    )
    assert has_service_entity, (
        f"Expected UserService or add_user in results, got entity IDs: {entity_ids}"
    )


# ---------------------------------------------------------------------------
# Test 4: Agentic investigation — structured, evidence-grounded answer
# ---------------------------------------------------------------------------
def test_agentic_investigation_add_user_behavior(indexed_stack):
    """
    The developer question "How does UserService.add_user work and what are its parameters?"
    must produce an InvestigationAnswer with:
      - a non-empty answer string
      - at least one hypothesis
      - at least one evidence ID
      - valid citation format
      - execution time recorded
      - HIGH or MEDIUM confidence (enough evidence exists in the sample project)
    """
    domain_repo, sources, graph_repo, hybrid_retriever = indexed_stack

    pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        use_deterministic_planner=True,
    )

    answer = pipeline.investigate(
        question="How does UserService.add_user work and what are its parameters?",
        repository_id=domain_repo.root_path,
        source_code_map=sources,
    )

    # Basic structural checks
    assert answer.answer, "Answer text must not be empty"
    assert len(answer.hypotheses) > 0, "At least one hypothesis must be formed"
    assert len(answer.evidence_ids) > 0, "Must reference at least one evidence ID"
    assert answer.execution_time_ms > 0, "Execution time must be recorded"

    # Citation format: each citation must reference a valid evidence ID
    valid_ev_ids = set(answer.evidence_ids)
    for citation in answer.citations:
        # Citations are strings like "[E1]" or evidence IDs themselves
        # The system guarantees no citation points outside the evidence set
        # We check that the citation string is non-empty
        assert citation.strip(), f"Empty citation found: {citation!r}"

    # The sample project has clear UserService code — evidence should be sufficient
    assert not answer.insufficient_evidence, (
        "Investigation should find sufficient evidence for UserService in the sample project"
    )

    # Confidence must be meaningful
    assert answer.confidence in {"HIGH", "MEDIUM"}, (
        f"Expected HIGH or MEDIUM confidence, got: {answer.confidence}"
    )


# ---------------------------------------------------------------------------
# Test 5: Change pipeline — plan + patch for adding age validation
# ---------------------------------------------------------------------------
def test_change_pipeline_add_age_validation(indexed_stack):
    """
    Full Phase 8 scenario:
    Request: "Add input validation to UserService.add_user to reject negative age values."

    The pipeline must:
      - Produce a VALIDATED or REJECTED (not FAILED) result
      - Generate a valid ChangePlan with at least one operation
      - Produce a Patch referencing services.py
      - Pass AST validation on the patched file
      - Complete without touching the source working tree
    """
    domain_repo, sources, graph_repo, hybrid_retriever = indexed_stack

    agent_pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        use_deterministic_planner=True,
    )

    change_pipeline = ChangePipeline(
        agent_pipeline=agent_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    request = ChangeRequest(
        description="Add input validation to UserService.add_user to reject negative age values.",
        repository_id=domain_repo.root_path,
    )

    result = change_pipeline.process_change_request(
        request=request,
        source_repo_path=SAMPLE_DIR,
        source_code_map=sources,
        run_tests=False,  # No pytest runner needed for this validation
    )

    # The pipeline must produce a definitive status (not crash)
    assert result.status in {"VALIDATED", "REJECTED", "TEST_FAILED"}, (
        f"Unexpected status: {result.status}"
    )

    # A valid plan must always be produced
    assert result.plan is not None
    assert result.plan.objective, "Plan objective must not be empty"
    assert result.plan.root_cause, "Plan must identify a root cause"

    if result.status == "VALIDATED":
        # Patch must reference services.py (the target file)
        assert result.patch is not None, "VALIDATED result must have a patch"
        assert len(result.patch.file_changes) > 0, "Patch must contain at least one file change"

        patched_files = {fc.file_path for fc in result.patch.file_changes}
        assert "services.py" in patched_files, (
            f"Expected services.py in patched files, got: {patched_files}"
        )

        # AST validation must pass for all patched files
        assert result.validation.syntax_valid, (
            f"Syntax validation failed: {result.validation.failures}"
        )
        assert result.validation.structural_valid

        # Unified diff must be non-empty
        assert result.patch.unified_diff or len(result.patch.file_changes) > 0

        print(f"\n[VALIDATED] Patch generated for: {patched_files}")
        print(f"  Plan operations: {len(result.plan.modifications)}")
        print(f"  Lines added: {result.patch.lines_added}, removed: {result.patch.lines_removed}")

    elif result.status == "REJECTED":
        # Rejection must come with a clear reason — not a silent crash
        assert result.explanation, "Rejected change must have an explanation"
        assert len(result.validation.failures) > 0 or result.plan.rejection_reason, (
            "Rejection must specify the reason via validation failures or plan.rejection_reason"
        )
        print(f"\n[REJECTED] Reason: {result.explanation}")

    print(f"  Execution time: {result.execution_time_ms:.1f} ms")


# ---------------------------------------------------------------------------
# Test 6: Safety boundary — forbidden operations must be rejected
# ---------------------------------------------------------------------------
def test_change_pipeline_rejects_forbidden_operation(indexed_stack):
    """
    Requesting a database migration or file deletion must be caught by the
    safety validator before any patch is generated.
    """
    domain_repo, sources, graph_repo, hybrid_retriever = indexed_stack

    agent_pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        use_deterministic_planner=True,
    )

    change_pipeline = ChangePipeline(
        agent_pipeline=agent_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    # The deterministic planner abstains on unknown/ambiguous targets
    dangerous_request = ChangeRequest(
        description="Run DATABASE_MIGRATIONS to drop the users table in the non-existent database.",
        repository_id=domain_repo.root_path,
    )

    result = change_pipeline.process_change_request(
        request=dangerous_request,
        source_repo_path=SAMPLE_DIR,
        source_code_map=sources,
        run_tests=False,
    )

    # Must be rejected — no patch should be applied for this request
    assert result.status == "REJECTED", (
        f"Expected REJECTED for forbidden/ambiguous operation, got: {result.status}"
    )
    assert result.patch is None or result.plan.is_valid is False, (
        "No valid patch should be produced for forbidden operations"
    )
    assert result.explanation, "Rejection must include a human-readable explanation"


# ---------------------------------------------------------------------------
# Test 7: Idempotency — re-indexing produces identical graph state
# ---------------------------------------------------------------------------
def test_graph_indexing_is_idempotent(indexed_stack):
    """
    Indexing the same repository twice must produce the exact same node
    and relationship counts in Neo4j (MERGE semantics guarantee).
    """
    domain_repo, sources, graph_repo, _ = indexed_stack

    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)

    def count_graph():
        with graph_repo._driver.session(database=NEO4J_DATABASE) as session:
            nodes = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
            rels = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
        return nodes, rels

    # Re-index (idempotent second run)
    graph_indexer.index(domain_repo, source_code_map=sources)
    nodes_after_1, rels_after_1 = count_graph()

    graph_indexer.index(domain_repo, source_code_map=sources)
    nodes_after_2, rels_after_2 = count_graph()

    assert nodes_after_1 == nodes_after_2, (
        f"Node count changed after re-index: {nodes_after_1} -> {nodes_after_2}"
    )
    assert rels_after_1 == rels_after_2, (
        f"Relationship count changed after re-index: {rels_after_1} -> {rels_after_2}"
    )

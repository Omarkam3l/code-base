"""
Dynamic end-to-end use case test for CodeGraph RAG — no mocks, no fixtures,
no hardcoded expectations.

Instead of a static sample project, this test targets THIS repository's own
source tree (src/). Every target, query, and assertion is derived at runtime
from the filesystem and the ingested domain model:

  Phase 1 — Ingest the real codegraph-rag source (Tree-sitter AST)
  Phase 2 — Index it into Neo4j (cleaning prior state for the repo first)
  Phase 3 — Hybrid retrieval with a query built from a dynamically chosen entity
  Phase 7 — Agentic investigation of a dynamically chosen method, with a
            grounding check that the answer actually names its target
  Phase 8 — Change pipeline run against the real repo, with a grounding check
            that any generated patch touches files that actually exist here

Credentials come exclusively from the environment — never from source control.
"""

import os
import random
from pathlib import Path

import pytest

from codegraph.agent.pipeline import AgenticPipeline
from codegraph.change.models import ChangeRequest
from codegraph.change.pipeline import ChangePipeline
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.graph.models import make_repository_id
from codegraph.graph.repository import GraphRepository
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.embeddings import BGEEmbeddingModel
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.vector_retriever import VectorRetriever
from codegraph.retrieval.vector_store import ChromaVectorStore
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

pytestmark = pytest.mark.skipif(
    not (NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD),
    reason="NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not set; skipping live integration tests",
)

# The target is this project's own source — located, never hardcoded.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src" / "codegraph"

EMBED_CACHE_DIR = PROJECT_ROOT / "data" / "embed_cache"


def _make_llm_provider():
    """Real LLM via NVIDIA NIM when a key is present; None keeps offline mode."""
    import os

    if os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY"):
        from codegraph.rag.llm import NvidiaLLMProvider

        return NvidiaLLMProvider()
    return None


def _embed_with_cache(texts: list[str], model) -> list[list[float]]:
    """Embed texts with a content-hash disk cache (bge-m3 on CPU is slow)."""
    import hashlib
    import json

    digest = hashlib.sha256("\x1e".join(texts).encode("utf-8")).hexdigest()[:24]
    cache_file = EMBED_CACHE_DIR / f"dynamic_usecase_{digest}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text())
        if len(cached) == len(texts):
            return cached
    vectors = model.embed_documents(texts)
    EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(vectors))
    return vectors


# ---------------------------------------------------------------------------
# Shared fixture: the real repository, fully indexed (graph + vector)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real_stack(tmp_path_factory):
    """Returns (domain_repo, sources, graph_repo, hybrid_retriever, target)."""
    assert SRC_DIR.is_dir(), f"Source tree not found at {SRC_DIR}"

    # A fresh (unseeded) pick each run — the use case must work for any target.
    rng = random.Random()

    # --- Phase 1: Ingest the real source tree ---
    ingestor = RepositoryIngestor(root=SRC_DIR)
    domain_repo = ingestor.ingest()
    sources = {f.path: (SRC_DIR / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # --- Phase 2 (chunking + embeddings first: bge-m3 on CPU is slow, and a
    # Neo4j connection opened before it may go stale before first use) ---
    chunker = CodeChunker()
    chunks = chunker.chunk_repository(domain_repo, source_code_map=sources)

    # Real embeddings (BAAI/bge-m3 via Hugging Face) — no mock vectors.
    embedding_model = BGEEmbeddingModel()
    doc_texts = [f"{c.entity_type} {c.qualified_name}\n{c.source_code}" for c in chunks]
    embeddings = _embed_with_cache(doc_texts, embedding_model)
    tmp_path = tmp_path_factory.mktemp("chroma")
    vector_store = ChromaVectorStore(
        collection_name="dynamic_usecase_chunks",
        persist_directory=tmp_path / "chroma",
    )
    vector_store.upsert(chunks=chunks, embeddings=embeddings)

    # --- Phase 3: Index into Neo4j, clearing prior state for this repo ---
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        max_connection_lifetime=300,  # don't reuse connections Aura may have dropped
    )
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)

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

    hybrid_retriever = HybridRetriever(
        vector_retriever=VectorRetriever(vector_store=vector_store, embedding_model=embedding_model),
        graph_retriever=GraphRetriever(graph_repo=graph_repo),
    )

    # --- Dynamically choose the investigation target ---
    # The class with the most methods in the codebase — a real, central entity.
    all_classes = [
        (f.path, cls)
        for f in domain_repo.files
        for cls in f.classes
        if cls.methods
    ]
    assert all_classes, "No classes with methods found in the real source tree"
    target_path, target_class = max(all_classes, key=lambda pc: len(pc[1].methods))
    target_method = rng.choice(target_class.methods)

    target = {
        "file": target_path,
        "class": target_class.name,
        "qualified_class": f"{Path(target_path).with_suffix('').as_posix().replace('/', '.')}.{target_class.name}",
        "method": target_method.name,
    }

    print(f"\n[dynamic target] {target['qualified_class']}.{target['method']} ({target['file']})")
    print(f"[indexed] files={index_result.file_count} classes={index_result.class_count} "
          f"relationships={index_result.relationship_count} chunks={len(chunks)}")

    yield domain_repo, sources, graph_repo, hybrid_retriever, target

    graph_repo.close()


# ---------------------------------------------------------------------------
# Test 1: Ingestion matches the actual filesystem — nothing static
# ---------------------------------------------------------------------------
def test_ingestion_reflects_real_filesystem(real_stack):
    domain_repo, sources, *_ = real_stack

    on_disk = {
        str(p.relative_to(SRC_DIR)).replace("\\", "/")
        for p in SRC_DIR.rglob("*.py")
    }
    ingested = {f.path for f in domain_repo.files}

    assert on_disk == ingested, (
        f"Ingested file set differs from disk:\n"
        f"  missing: {sorted(on_disk - ingested)}\n"
        f"  extra:   {sorted(ingested - on_disk)}"
    )
    assert len(domain_repo.failed_files) == 0, "No real source file should fail to parse"
    # Every ingested file's content must be byte-identical to the disk file.
    for f in domain_repo.files:
        assert sources[f.path] == (SRC_DIR / f.path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 2: The dynamically chosen target exists in the Neo4j graph
# ---------------------------------------------------------------------------
def test_dynamic_target_exists_in_graph(real_stack):
    _, _, graph_repo, _, target = real_stack

    node = graph_repo.find_class(target["qualified_class"])
    assert node is not None, f"{target['qualified_class']} not found in graph"
    assert node["name"] == target["class"]


# ---------------------------------------------------------------------------
# Test 3: Hybrid retrieval finds the dynamically chosen target
# ---------------------------------------------------------------------------
def test_hybrid_retrieval_finds_dynamic_target(real_stack):
    domain_repo, _, _, hybrid_retriever, target = real_stack

    query = f"{target['class']} {target['method']}"  # built from the live target
    results = hybrid_retriever.retrieve(
        query=query, repository_id=domain_repo.root_path, limit=10
    )

    assert results, "Hybrid retriever returned nothing for a real central entity"
    entity_ids = {r.entity_id for r in results}
    assert any(
        target["class"] in eid or target["method"] in eid for eid in entity_ids
    ), f"{target['class']}/{target['method']} not among retrieved entities: {entity_ids}"


# ---------------------------------------------------------------------------
# Test 4: Agentic investigation answers a question about the dynamic target,
#          and the answer is grounded (names the entity it investigated)
# ---------------------------------------------------------------------------
def test_agentic_investigation_is_grounded(real_stack):
    domain_repo, sources, graph_repo, hybrid_retriever, target = real_stack

    pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        # Real LLM (NVIDIA NIM) synthesizes the answer from gathered evidence;
        # deterministic planner keeps the investigation steps reproducible.
        llm_provider=_make_llm_provider(),
        use_deterministic_planner=True,
    )
    question = (
        f"How does {target['class']}.{target['method']} work and what does it do?"
    )
    answer = pipeline.investigate(
        question=question,
        repository_id=domain_repo.root_path,
        source_code_map=sources,
    )

    assert answer.answer, "Answer text must not be empty"
    assert answer.hypotheses, "At least one hypothesis must be formed"
    assert answer.evidence_ids, "Must reference at least one evidence ID"
    assert answer.execution_time_ms > 0
    assert not answer.insufficient_evidence, (
        f"Investigation of a real, graph-present entity ({target['qualified_class']}) "
        "should find sufficient evidence"
    )
    assert answer.confidence in {"HIGH", "MEDIUM"}, f"Got confidence: {answer.confidence}"

    # Grounding: the answer must actually talk about the entity it was asked about.
    hypothesis_text = " ".join(str(h) for h in answer.hypotheses)
    haystack = (answer.answer + " " + hypothesis_text).lower()
    assert target["class"].lower() in haystack or target["method"].lower() in haystack, (
        f"Answer does not mention {target['class']}.{target['method']} — it is not grounded "
        "in the question that was asked"
    )
    print(f"\n[answer] {answer.answer[:300]}...")


# ---------------------------------------------------------------------------
# Test 5: Change pipeline on the real repo — any patch must be grounded in
#          files that actually exist in this repository
# ---------------------------------------------------------------------------
def test_change_pipeline_grounded_in_real_repo(real_stack):
    domain_repo, sources, graph_repo, hybrid_retriever, target = real_stack

    change_pipeline = ChangePipeline(
        agent_pipeline=AgenticPipeline(
            graph_repo=graph_repo,
            hybrid_retriever=hybrid_retriever,
            llm_provider=_make_llm_provider(),
            use_deterministic_planner=True,
        ),
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    request = ChangeRequest(
        description=(
            f"Add input validation to {target['class']}.{target['method']} "
            f"in {target['file']} to reject invalid arguments."
        ),
        repository_id=domain_repo.root_path,
    )

    result = change_pipeline.process_change_request(
        request=request,
        source_repo_path=SRC_DIR,
        source_code_map=sources,
        run_tests=False,
    )

    assert result.status in {"VALIDATED", "REJECTED", "TEST_FAILED"}, (
        f"Pipeline crashed or returned unexpected status: {result.status}"
    )
    assert result.plan is not None and result.plan.objective

    if result.status == "VALIDATED":
        assert result.patch is not None and result.patch.file_changes
        patched_files = {fc.file_path for fc in result.patch.file_changes}
        # GROUNDING: a patch for this repo may only touch files that exist here.
        ungrounded = patched_files - set(sources)
        assert not ungrounded, (
            f"Patch modifies files that do not exist in the repository: {ungrounded}. "
            f"The planner is not grounded in the real codebase (request targeted "
            f"{target['file']})."
        )
        assert target["file"] in patched_files, (
            f"Patch touched {patched_files} but the request targeted {target['file']}"
        )
        assert result.validation.syntax_valid
        print(f"\n[VALIDATED] grounded patch for: {patched_files}")
    else:
        assert result.explanation, "Rejection must include an explanation"
        print(f"\n[{result.status}] {result.explanation[:200]}")

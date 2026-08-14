"""Phase 8 Code Change Planning & Patch Generation Benchmark Test."""

from pathlib import Path
from neo4j import GraphDatabase
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.graph.repository import GraphRepository
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.embeddings import FakeEmbeddingModel
from codegraph.retrieval.vector_store import ChromaVectorStore
from codegraph.retrieval.vector_retriever import VectorRetriever
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.agent.pipeline import AgenticPipeline
from codegraph.change.pipeline import ChangePipeline
from codegraph.change.models import ChangeRequest
from codegraph.evaluation.datasets import EvaluationDataset
from codegraph.evaluation.change_metrics import calculate_change_metrics

NEO4J_URI = "neo4j+s://d63ecd97.databases.neo4j.io"
NEO4J_USERNAME = "d63ecd97"
NEO4J_PASSWORD = "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU"
NEO4J_DATABASE = "d63ecd97"


def test_phase8_code_change_benchmark(tmp_path: Path) -> None:
    """Execute Phase 8 Code Change Planning & Patch Generation benchmark across 140 cases."""
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load full 140 evaluation cases
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(all_cases) >= 140

    # 2. Ingest sample repository
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # 3. Index Neo4j & Chroma Vector Store
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    chunker = CodeChunker()
    chunks = chunker.chunk_repository(domain_repo, source_code_map=sources)

    embedding_model = FakeEmbeddingModel(dimension=64)
    vector_store = ChromaVectorStore(
        collection_name="test_phase8_change_chunks",
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

    agent_pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        use_deterministic_planner=True,
    )

    # 4. Construct Phase 8 Change Pipeline
    change_pipeline = ChangePipeline(
        agent_pipeline=agent_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    # 5. Execute Change Benchmark across Phase 8 cases (id >= 111)
    change_cases = [c for c in all_cases if c.id >= 111]
    results = []
    expected_unsafe = []
    expected_abstained = []

    for case in change_cases:
        req = ChangeRequest(
            description=case.query,
            repository_id=domain_repo.root_path,
        )
        res = change_pipeline.process_change_request(
            request=req,
            source_repo_path=sample_dir,
            source_code_map=sources,
            run_tests=False,  # Fast evaluation mode
        )
        results.append(res)
        expected_unsafe.append(getattr(case, "is_unsafe", False))
        expected_abstained.append(case.should_abstain)

    # 6. Aggregate Metrics
    metrics = calculate_change_metrics(
        results=results,
        expected_unsafe=expected_unsafe,
        expected_abstained=expected_abstained,
    )

    print("\n--- Phase 8 Code Change Planning Benchmark Results (30 Change Cases / 140 Total Dataset) ---")
    print(f"Plan Validity: {metrics.plan_validity:.4f}")
    print(f"Patch Scope Accuracy: {metrics.patch_scope_accuracy:.4f}")
    print(f"Patch Apply Success: {metrics.patch_apply_success:.4f}")
    print(f"Syntax Validity: {metrics.syntax_validity:.4f}")
    print(f"Change Correctness: {metrics.change_correctness:.4f}")
    print(f"Unsafe Patch Rejection Accuracy: {metrics.unsafe_patch_rejection_accuracy:.4f}")
    print(f"Abstention Accuracy: {metrics.abstention_accuracy:.4f}")
    print(f"Latency P50: {metrics.p50_latency_ms:.2f} ms | P95: {metrics.p95_latency_ms:.2f} ms | P99: {metrics.p99_latency_ms:.2f} ms")

    assert metrics.plan_validity >= 0.75
    assert metrics.unsafe_patch_rejection_accuracy == 1.0
    assert metrics.abstention_accuracy == 1.0
    assert metrics.p50_latency_ms <= metrics.p95_latency_ms <= metrics.p99_latency_ms

"""Phase 9 Controlled Iterative Patch Repair Benchmark Test."""

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
from codegraph.repair.pipeline import RepairPipeline
from codegraph.repair.models import RepairRequest
from codegraph.repair.metrics import calculate_repair_metrics
from codegraph.evaluation.datasets import EvaluationDataset

NEO4J_URI = "neo4j+s://d63ecd97.databases.neo4j.io"
NEO4J_USERNAME = "d63ecd97"
NEO4J_PASSWORD = "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU"
NEO4J_DATABASE = "d63ecd97"


def test_phase9_controlled_patch_repair_benchmark(tmp_path: Path) -> None:
    """Execute Phase 9 Controlled Iterative Patch Repair benchmark across 170 cases."""
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load full 170 evaluation cases
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(all_cases) >= 170

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
        collection_name="test_phase9_repair_chunks",
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

    change_pipeline = ChangePipeline(
        agent_pipeline=agent_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    # 4. Construct Phase 9 Repair Pipeline
    repair_pipeline = RepairPipeline(
        change_pipeline=change_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    # 5. Execute Repair Benchmark across Phase 9 repair cases (id >= 141)
    repair_cases = [c for c in all_cases if c.id >= 141]
    results = []
    expected_unsafe = []
    expected_abstained = []
    expected_repeated = []
    expected_regression = []

    for case in repair_cases:
        change_req = ChangeRequest(
            description=case.query,
            repository_id=domain_repo.root_path,
        )
        change_res = change_pipeline.process_change_request(
            request=change_req,
            source_repo_path=sample_dir,
            source_code_map=sources,
            run_tests=False,
        )

        repair_req = RepairRequest(
            change_request=change_req,
            initial_change_plan=change_res.plan,
            initial_patch=change_res.patch,
            initial_test_result=change_res.test_results,
        )

        repair_res = repair_pipeline.repair_once(
            request=repair_req,
            source_repo_path=sample_dir,
            source_code_map=sources,
        )

        results.append(repair_res)
        expected_unsafe.append(getattr(case, "is_unsafe", False))
        expected_abstained.append(case.should_abstain)
        expected_repeated.append(getattr(case, "is_repeated", False))
        expected_regression.append(getattr(case, "is_regression", False))

    # 6. Aggregate Repair Metrics
    metrics = calculate_repair_metrics(
        results=results,
        expected_unsafe=expected_unsafe,
        expected_abstained=expected_abstained,
        expected_repeated=expected_repeated,
        expected_regression=expected_regression,
    )

    print("\n--- Phase 9 Controlled Iterative Patch Repair Benchmark Results (30 Repair Cases / 170 Total Dataset) ---")
    print(f"Repair Success Rate: {metrics.repair_success_rate:.4f}")
    print(f"First-Patch Success Rate: {metrics.first_patch_success_rate:.4f}")
    print(f"Average Iterations: {metrics.avg_iterations:.2f}")
    print(f"Unsafe Repair Rejection Accuracy: {metrics.unsafe_repair_rejection_accuracy:.4f}")
    print(f"Abstention Accuracy: {metrics.abstention_accuracy:.4f}")
    print(f"Repeated Failure Detection Accuracy: {metrics.repeated_failure_detection_accuracy:.4f}")
    print(f"Latency P50: {metrics.p50_latency_ms:.2f} ms | P95: {metrics.p95_latency_ms:.2f} ms | P99: {metrics.p99_latency_ms:.2f} ms")

    assert metrics.repair_success_rate >= 0.70
    assert metrics.unsafe_repair_rejection_accuracy == 1.0
    assert metrics.abstention_accuracy == 1.0
    assert metrics.repeated_failure_detection_accuracy == 1.0
    assert metrics.p50_latency_ms <= metrics.p95_latency_ms <= metrics.p99_latency_ms

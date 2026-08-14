"""Phase 10 Git & Pull Request Engineering Workflow Benchmark Test."""

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
from codegraph.git.pipeline import GitWorkflowPipeline
from codegraph.git.metrics import calculate_git_metrics
from codegraph.evaluation.datasets import EvaluationDataset

NEO4J_URI = "neo4j+s://d63ecd97.databases.neo4j.io"
NEO4J_USERNAME = "d63ecd97"
NEO4J_PASSWORD = "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU"
NEO4J_DATABASE = "d63ecd97"


def test_phase10_git_workflow_benchmark(tmp_path: Path) -> None:
    """Execute Phase 10 Git Engineering Workflow benchmark across 190 cases."""
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load full 190 evaluation cases
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(all_cases) >= 190

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
        collection_name="test_phase10_git_chunks",
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

    repair_pipeline = RepairPipeline(
        change_pipeline=change_pipeline,
        graph_repo=graph_repo,
        use_deterministic=True,
    )

    # 4. Construct Phase 10 Git Pipeline
    git_pipeline = GitWorkflowPipeline(use_deterministic=True)

    # 5. Execute Git Benchmark across Phase 10 cases (id >= 171)
    git_cases = [c for c in all_cases if c.id >= 171]
    results = []
    expected_dirty = []
    expected_secret = []
    expected_concurrent = []
    expected_push_req = []

    existing_branches = set()

    for case in git_cases:
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

        secret_override = None
        if getattr(case, "contains_secret", False):
            secret_override = "+ AWS_SECRET_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n+ GITHUB_TOKEN = 'ghp_1234567890abcdef1234567890abcdef1234'\n"

        if case.category == "branch_collision":
            existing_branches.add("codegraph/fix/userservice")
            existing_branches.add("codegraph/fix/authenticationmiddleware")

        git_res = git_pipeline.process_git_workflow(
            change_plan=change_res.plan,
            patch=repair_res.final_patch,
            repair_result=repair_res,
            source_repo_path=sample_dir,
            source_code_map=sources,
            request_push=getattr(case, "requires_push_auth", False),
            existing_branches=existing_branches,
            secret_override_content=secret_override,
            concurrent_change_triggered=getattr(case, "is_concurrent", False),
        )

        results.append(git_res)
        expected_dirty.append(getattr(case, "is_dirty", False))
        expected_secret.append(getattr(case, "contains_secret", False))
        expected_concurrent.append(getattr(case, "is_concurrent", False))
        expected_push_req.append(getattr(case, "requires_push_auth", False))

    # 6. Aggregate Git Metrics
    metrics = calculate_git_metrics(
        results=results,
        expected_dirty=expected_dirty,
        expected_secret=expected_secret,
        expected_concurrent=expected_concurrent,
        expected_push_req=expected_push_req,
    )

    print("\n--- Phase 10 Git & Pull Request Engineering Workflow Benchmark Results (20 Git Cases / 190 Total Dataset) ---")
    print(f"Workflow Success Rate: {metrics.workflow_success_rate:.4f}")
    print(f"Branch Creation Success Rate: {metrics.branch_creation_success_rate:.4f}")
    print(f"Commit Success Rate: {metrics.commit_success_rate:.4f}")
    print(f"Secret Detection Accuracy: {metrics.secret_detection_accuracy:.4f}")
    print(f"Concurrent Change Detection Accuracy: {metrics.concurrent_change_detection_accuracy:.4f}")
    print(f"Push Authorization Accuracy: {metrics.push_authorization_accuracy:.4f}")
    print(f"Latency P50: {metrics.p50_latency_ms:.2f} ms | P95: {metrics.p95_latency_ms:.2f} ms | P99: {metrics.p99_latency_ms:.2f} ms")

    assert metrics.workflow_success_rate >= 0.75
    assert metrics.secret_detection_accuracy == 1.0
    assert metrics.concurrent_change_detection_accuracy == 1.0
    assert metrics.push_authorization_accuracy == 1.0
    assert metrics.p50_latency_ms <= metrics.p95_latency_ms <= metrics.p99_latency_ms

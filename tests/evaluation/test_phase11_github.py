"""Phase 11 Real GitHub Integration, CI Monitoring & PR Review Loop Benchmark Test."""

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
from codegraph.repair.pipeline import RepairPipeline
from codegraph.git.pipeline import GitWorkflowPipeline
from codegraph.github.pipeline import GitHubWorkflowPipeline
from codegraph.github.client import FakeGitHubClient
from codegraph.github.models import GitHubEvent
from codegraph.github.metrics import calculate_github_metrics
from codegraph.evaluation.datasets import EvaluationDataset

NEO4J_URI = "neo4j+s://d63ecd97.databases.neo4j.io"
NEO4J_USERNAME = "d63ecd97"
NEO4J_PASSWORD = "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU"
NEO4J_DATABASE = "d63ecd97"


def test_phase11_github_integration_benchmark(tmp_path: Path) -> None:
    """Execute Phase 11 GitHub integration benchmark across 210 total cases."""
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load full 210 evaluation cases
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(all_cases) >= 210

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
        collection_name="test_phase11_github_chunks",
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

    git_pipeline = GitWorkflowPipeline(use_deterministic=True)

    # 4. Construct Phase 11 GitHub Workflow Pipeline
    github_client = FakeGitHubClient()
    github_pipeline = GitHubWorkflowPipeline(
        client=github_client,
        change_pipeline=change_pipeline,
        repair_pipeline=repair_pipeline,
        git_pipeline=git_pipeline,
        use_deterministic=True,
    )

    # 5. Execute GitHub Benchmark across Phase 11 cases (id >= 191)
    github_cases = [c for c in all_cases if c.id >= 191]
    results = []
    expected_ci_fail = []
    expected_review = []

    for case in github_cases:
        event = GitHubEvent(
            event_id=f"evt_{case.id}",
            event_type="review_comment" if getattr(case, "is_review_comment", False) else "pr_opened",
            repository="Omarkam3l/code-base",
            pr_number=101,
            branch="codegraph/fix/userservice-auth",
            sender="user1",
            payload={
                "pull_request": {"title": case.query, "body": "Investigation instruction"},
                "comment": {"body": case.query, "path": "services.py", "line": 42},
            },
        )

        sim_ci = getattr(case, "is_ci_failure", False)
        sim_rev = getattr(case, "is_review_comment", False)

        gh_res = github_pipeline.process_event(
            event=event,
            source_repo_path=sample_dir,
            source_code_map=sources,
            simulated_ci_fail=sim_ci,
            simulated_review_comment=sim_rev,
        )

        results.append(gh_res)
        expected_ci_fail.append(sim_ci)
        expected_review.append(sim_rev)

    # 6. Aggregate GitHub Metrics
    metrics = calculate_github_metrics(
        results=results,
        expected_ci_fail=expected_ci_fail,
        expected_review=expected_review,
    )

    print("\n--- Phase 11 Real GitHub Integration, CI Monitoring & PR Review Loop Benchmark Results (20 GitHub Cases / 210 Total Dataset) ---")
    print(f"Workflow Success Rate: {metrics.workflow_success_rate:.4f}")
    print(f"PR Creation Success Rate: {metrics.pr_creation_success_rate:.4f}")
    print(f"CI Event Processing Accuracy: {metrics.ci_processing_accuracy:.4f}")
    print(f"Review Comment Accuracy: {metrics.review_comment_accuracy:.4f}")
    print(f"Latency P50: {metrics.p50_latency_ms:.2f} ms | P95: {metrics.p95_latency_ms:.2f} ms | P99: {metrics.p99_latency_ms:.2f} ms")

    assert metrics.workflow_success_rate >= 0.75
    assert metrics.pr_creation_success_rate == 1.0
    assert metrics.ci_processing_accuracy == 1.0
    assert metrics.review_comment_accuracy == 1.0
    assert metrics.p50_latency_ms <= metrics.p95_latency_ms <= metrics.p99_latency_ms

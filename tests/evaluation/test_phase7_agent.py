"""Evaluation benchmark suite for Phase 7 Agentic Codebase Investigation across 110 cases."""

import os
from pathlib import Path
from neo4j import GraphDatabase

from codegraph.agent.pipeline import AgenticPipeline
from codegraph.evaluation.agent_metrics import calculate_agent_metrics
from codegraph.evaluation.datasets import EvaluationDataset
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.graph.repository import GraphRepository
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.embeddings import FakeEmbeddingModel
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.vector_retriever import VectorRetriever
from codegraph.retrieval.vector_store import ChromaVectorStore

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


def test_phase7_agentic_investigation_benchmark(tmp_path: Path) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load 110 cases
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(all_cases) >= 110

    # 2. Ingest repository
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # 3. Neo4j & Chroma Indexing
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    chunker = CodeChunker()
    chunks = chunker.chunk_repository(domain_repo, source_code_map=sources)
    chunk_map = {c.id: c for c in chunks}

    embedding_model = FakeEmbeddingModel(dimension=64)
    vector_store = ChromaVectorStore(
        collection_name="test_phase7_agent_chunks",
        persist_directory=tmp_path / "chroma",
    )

    doc_texts = [f"{c.entity_type} {c.qualified_name}\n{c.source_code}" for c in chunks]
    embeddings = embedding_model.embed_documents(doc_texts)
    vector_store.upsert(chunks=chunks, embeddings=embeddings)

    vector_retriever = VectorRetriever(vector_store=vector_store, embedding_model=embedding_model)

    from codegraph.retrieval.graph_retriever import GraphRetriever
    graph_retriever = GraphRetriever(graph_repo=graph_repo)
    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        graph_retriever=graph_retriever,
    )

    # 4. Construct Phase 7 Agentic Pipeline
    pipeline = AgenticPipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        use_deterministic_planner=True,
    )

    # 5. Execute Investigation Benchmark across 110 Cases
    answers = []
    expected_root_causes = []
    expected_insufficient = []

    agent_cases = [c for c in all_cases if 80 < c.id <= 110]
    for case in agent_cases:
        ans = pipeline.investigate(
            question=case.query,
            repository_id=domain_repo.root_path,
            source_code_map=sources,
        )
        answers.append(ans)
        exp_rc = case.expected_entities[0] if case.expected_entities else None
        expected_root_causes.append(exp_rc)
        expected_insufficient.append(case.should_abstain)

    # 6. Aggregate Metrics
    metrics = calculate_agent_metrics(
        answers=answers,
        expected_root_causes=expected_root_causes,
        expected_insufficient=expected_insufficient,
    )

    print("\n--- Phase 7 Agentic Investigation Benchmark Results (110 Cases) ---")
    print(f"Investigation Success Rate: {metrics.investigation_success_rate:.4f}")
    print(f"Root Cause Accuracy: {metrics.root_cause_accuracy:.4f}")
    print(f"Evidence Sufficiency: {metrics.evidence_sufficiency:.4f}")
    print(f"Abstention Accuracy: {metrics.abstention_accuracy:.4f}")
    print(f"Citation Validity: {metrics.citation_validity:.4f}")
    print(f"Tool Efficiency: {metrics.tool_efficiency:.4f}")
    print(f"Avg Tool Calls: {metrics.avg_tool_calls:.2f}")
    print(f"Latency P50: {metrics.p50_latency_ms:.2f} ms | P95: {metrics.p95_latency_ms:.2f} ms | P99: {metrics.p99_latency_ms:.2f} ms")

    assert metrics.investigation_success_rate >= 0.90
    assert metrics.abstention_accuracy >= 0.80
    assert metrics.citation_validity == 1.0
    assert metrics.tool_efficiency >= 0.50

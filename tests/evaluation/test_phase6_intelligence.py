"""Phase 6 Code Intelligence evaluation benchmark test across 80 cases."""

import os
from pathlib import Path
import pytest
from neo4j import GraphDatabase

from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.graph.repository import GraphRepository
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.retrieval.embeddings import FakeEmbeddingModel
from codegraph.retrieval.vector_store import ChromaVectorStore
from codegraph.retrieval.indexer import VectorIndexer
from codegraph.retrieval.vector_retriever import VectorRetriever
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.hybrid import HybridRetriever

from codegraph.rag.llm import FakeLLMProvider
from codegraph.intelligence import CodeIntelligencePipeline
from codegraph.evaluation.datasets import EvaluationDataset
from codegraph.evaluation.intelligence_metrics import (
    calculate_architecture_coverage,
    calculate_correct_path_rate,
    calculate_dependency_accuracy,
    calculate_impact_coverage,
    calculate_path_precision,
    calculate_path_recall,
)
from codegraph.evaluation.metrics import compute_percentile

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


def test_phase6_code_intelligence_benchmark(tmp_path: Path) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load 80-case dataset
    cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    assert len(cases) == 80

    # 2. Ingest repository & index into Neo4j + Chroma
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    embedding_model = FakeEmbeddingModel(dimension=384)
    vector_store = ChromaVectorStore(
        collection_name="test_phase6_intelligence_chunks",
        persist_directory=tmp_path / "chroma",
    )
    vector_indexer = VectorIndexer(vector_store=vector_store, embedding_model=embedding_model)
    chunks = vector_indexer.index(domain_repo, source_code_map=sources)
    chunk_map = {c.entity_id: c for c in chunks}

    vector_retriever = VectorRetriever(vector_store=vector_store, embedding_model=embedding_model)
    graph_retriever = GraphRetriever(graph_repo=graph_repo)
    hybrid_retriever = HybridRetriever(vector_retriever=vector_retriever, graph_retriever=graph_retriever)

    # 3. Create Code Intelligence Pipeline
    pipeline = CodeIntelligencePipeline(
        graph_repo=graph_repo,
        hybrid_retriever=hybrid_retriever,
        reasoning_engine=None,  # Uses default FakeLLMProvider
    )

    # 4. Run Benchmark across all 80 Cases
    path_recalls: list[float] = []
    correct_path_rates: list[float] = []
    path_precisions: list[float] = []
    impact_coverages: list[float] = []
    dep_accuracies: list[float] = []
    arch_coverages: list[float] = []
    abstention_corrs: list[float] = []
    latencies_ms: list[float] = []

    for case in cases:
        res = pipeline.analyze(
            query=case.query,
            repository_id=domain_repo.root_path,
            source_code_map=sources,
            chunk_map=chunk_map,
        )
        latencies_ms.append(res.execution_time_ms)

        if case.should_abstain:
            if res.answer and res.answer.insufficient_evidence:
                abstention_corrs.append(1.0)
            else:
                abstention_corrs.append(0.0)
        else:
            if res.paths:
                rec = calculate_path_recall(res.paths, case.expected_entities)
                c_rate = calculate_correct_path_rate(res.paths, case.expected_entities)
                prec = calculate_path_precision(res.paths, case.expected_entities)
                path_recalls.append(rec)
                correct_path_rates.append(c_rate)
                path_precisions.append(prec)

            if res.impact:
                cov = calculate_impact_coverage(res.impact, case.expected_entities)
                impact_coverages.append(cov)

            if res.dependency:
                acc = calculate_dependency_accuracy(res.dependency, case.expected_entities)
                dep_accuracies.append(acc)

            if res.architecture:
                acov = calculate_architecture_coverage(res.architecture, case.expected_entities)
                arch_coverages.append(acov)

    # Calculate Percentiles
    p50 = compute_percentile(latencies_ms, 0.50)
    p95 = compute_percentile(latencies_ms, 0.95)
    p99 = compute_percentile(latencies_ms, 0.99)
    avg_lat = sum(latencies_ms) / len(latencies_ms)

    abst_acc = (sum(abstention_corrs) / len(abstention_corrs)) if abstention_corrs else 1.0

    print(f"\n--- Phase 6 Code Intelligence Benchmark Results (80 Cases) ---")
    print(f"Path Recall: {sum(path_recalls)/max(1, len(path_recalls)):.4f}")
    print(f"Correct Path Rate: {sum(correct_path_rates)/max(1, len(correct_path_rates)):.4f}")
    print(f"Path Precision: {sum(path_precisions)/max(1, len(path_precisions)):.4f}")
    print(f"Abstention Accuracy: {abst_acc:.4f}")
    print(f"Latency P50: {p50:.2f} ms | P95: {p95:.2f} ms | P99: {p99:.2f} ms | Avg: {avg_lat:.2f} ms")

    assert abst_acc == 1.0
    assert p50 < 1000.0  # Latency under 1s

    graph_repo.close()

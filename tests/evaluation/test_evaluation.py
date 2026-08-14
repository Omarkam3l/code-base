"""Retrieval evaluation benchmark test comparing Vector, Graph, and Hybrid strategies."""

import json
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
from codegraph.retrieval.evaluation import evaluate_retrieval_cases, BenchmarkReport

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


@pytest.fixture
def eval_cases() -> list[dict]:
    cases_file = Path("tests/evaluation/retrieval_cases.json")
    assert cases_file.exists()
    return json.loads(cases_file.read_text(encoding="utf-8"))


def test_retrieval_evaluation_benchmark(eval_cases: list[dict], tmp_path: Path) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Ingest sample repository
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # 2. Index into Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    # 3. Index into Chroma Vector Store
    embedding_model = FakeEmbeddingModel(dimension=384)
    vector_store = ChromaVectorStore(
        collection_name="test_eval_chunks",
        persist_directory=tmp_path / "chroma",
    )
    vector_indexer = VectorIndexer(vector_store=vector_store, embedding_model=embedding_model)
    vector_indexer.index(domain_repo, source_code_map=sources)

    # 4. Instantiate Retrievers
    vector_retriever = VectorRetriever(vector_store=vector_store, embedding_model=embedding_model)
    graph_retriever = GraphRetriever(graph_repo=graph_repo)
    hybrid_retriever = HybridRetriever(vector_retriever=vector_retriever, graph_retriever=graph_retriever)

    # 5. Run Evaluation Benchmark
    repo_id = domain_repo.root_path
    report = evaluate_retrieval_cases(
        cases=eval_cases,
        vector_retriever=vector_retriever,
        graph_retriever=graph_retriever,
        hybrid_retriever=hybrid_retriever,
    )

    table = report.to_formatted_table()
    print("\n\n" + table + "\n")

    assert isinstance(report, BenchmarkReport)
    assert report.hybrid_metrics.recall_at_5 > 0.0
    assert report.hybrid_metrics.mrr > 0.0

    graph_repo.close()

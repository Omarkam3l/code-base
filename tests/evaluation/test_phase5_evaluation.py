"""Phase 5 full evaluation benchmark and report artifact generator."""

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
from codegraph.rag.query_analyzer import QueryAnalyzer
from codegraph.rag.retrieval_planner import RetrievalPlanner
from codegraph.rag.context_expander import ContextExpander
from codegraph.rag.evidence import EvidenceBuilder
from codegraph.rag.answer_generator import AnswerGenerator
from codegraph.rag.pipeline import GraphRAGPipeline

from codegraph.evaluation.datasets import EvaluationDataset
from codegraph.evaluation.runner import BenchmarkRunner
from codegraph.evaluation.report import ReportGenerator

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


def test_phase5_full_evaluation_benchmark(tmp_path: Path) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Load 50-case Phase 5 evaluation dataset
    all_cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")
    cases = tuple(c for c in all_cases if c.id <= 50)
    assert len(cases) == 50

    # 2. Ingest repository
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # 3. Neo4j & Chroma Indexing
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    embedding_model = FakeEmbeddingModel(dimension=384)
    vector_store = ChromaVectorStore(
        collection_name="test_phase5_eval_chunks",
        persist_directory=tmp_path / "chroma",
    )
    vector_indexer = VectorIndexer(vector_store=vector_store, embedding_model=embedding_model)
    chunks = vector_indexer.index(domain_repo, source_code_map=sources)
    chunk_map = {c.entity_id: c for c in chunks}

    # 4. Phase 3 & 4 Components
    vector_retriever = VectorRetriever(vector_store=vector_store, embedding_model=embedding_model)
    graph_retriever = GraphRetriever(graph_repo=graph_repo)
    hybrid_retriever = HybridRetriever(vector_retriever=vector_retriever, graph_retriever=graph_retriever)

    llm_provider = FakeLLMProvider()
    query_analyzer = QueryAnalyzer(llm_provider=llm_provider)
    retrieval_planner = RetrievalPlanner()
    context_expander = ContextExpander(graph_repo=graph_repo)
    evidence_builder = EvidenceBuilder()
    answer_generator = AnswerGenerator(llm_provider=llm_provider)

    pipeline = GraphRAGPipeline(
        query_analyzer=query_analyzer,
        retrieval_planner=retrieval_planner,
        hybrid_retriever=hybrid_retriever,
        context_expander=context_expander,
        evidence_builder=evidence_builder,
        answer_generator=answer_generator,
    )

    # 5. Run Benchmark Runner across 50 Cases
    runner = BenchmarkRunner(
        vector_retriever=vector_retriever,
        graph_retriever=graph_retriever,
        hybrid_retriever=hybrid_retriever,
        graph_rag_pipeline=pipeline,
    )

    report = runner.run_benchmark(
        cases=cases,
        repository_id=domain_repo.root_path,
        chunk_map=chunk_map,
        baseline_file="tests/evaluation/baseline.json",
    )

    # 6. Format Markdown Report Artifact
    reporter = ReportGenerator()
    md_content = reporter.generate_markdown_report(report, output_path=tmp_path / "evaluation_report.md")

    print("\n\n" + reporter.format_overall_table(report) + "\n")

    assert report.quality_gate_passed
    assert report.overall_metrics["graph_rag"].citation_validity == 1.0
    assert report.overall_metrics["graph_rag"].abstention_accuracy == 1.0

    graph_repo.close()

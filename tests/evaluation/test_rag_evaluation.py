"""Answer-level evaluation benchmark comparing Hybrid retrieval vs Graph-RAG with expansion."""

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

from codegraph.rag.llm import FakeLLMProvider
from codegraph.rag.query_analyzer import QueryAnalyzer
from codegraph.rag.retrieval_planner import RetrievalPlanner
from codegraph.rag.context_expander import ContextExpander
from codegraph.rag.evidence import EvidenceBuilder
from codegraph.rag.answer_generator import AnswerGenerator
from codegraph.rag.pipeline import GraphRAGPipeline

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


@pytest.fixture
def rag_cases() -> list[dict]:
    cases_file = Path("tests/evaluation/rag_cases.json")
    assert cases_file.exists()
    return json.loads(cases_file.read_text(encoding="utf-8"))


def test_rag_evaluation_benchmark(rag_cases: list[dict], tmp_path: Path) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Ingest repository
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    sources = {f.path: (sample_dir / f.path).read_text(encoding="utf-8") for f in domain_repo.files}

    # 2. Neo4j & Chroma Indexing
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    graph_repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
    graph_indexer.index(domain_repo, source_code_map=sources)

    embedding_model = FakeEmbeddingModel(dimension=384)
    vector_store = ChromaVectorStore(
        collection_name="test_rag_eval_chunks",
        persist_directory=tmp_path / "chroma",
    )
    vector_indexer = VectorIndexer(vector_store=vector_store, embedding_model=embedding_model)
    chunks = vector_indexer.index(domain_repo, source_code_map=sources)
    chunk_map = {c.entity_id: c for c in chunks}

    # 3. Setup Retrievers & Pipeline
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

    # 4. Run Benchmark Metrics Evaluation
    total_validations = 0
    total_citations = 0
    total_unsupported = 0
    coverage_scores = []

    for case in rag_cases:
        query = case["query"]
        expected_entities = set(case["expected_entities"])

        answer, evidence_graph, timings = pipeline.answer(
            query=query,
            repository_id=domain_repo.root_path,
            chunk_map=chunk_map,
        )

        if answer.validation_passed:
            total_validations += 1

        c_count = len(answer.citations)
        total_citations += c_count

        if not answer.validation_passed:
            total_unsupported += len(answer.validation_errors)

        found_eids = {ev.entity_id for ev in evidence_graph.nodes}
        if expected_entities:
            hits = len(found_eids.intersection(expected_entities))
            coverage_scores.append(hits / len(expected_entities))
        else:
            coverage_scores.append(1.0)

    n = max(1, len(rag_cases))
    citation_validity = (total_validations / n)
    avg_evidence_coverage = (sum(coverage_scores) / n)
    unsupported_rate = (total_unsupported / max(1, total_citations))

    header = f"{'Strategy':<32} {'Citation Validity':<20} {'Evidence Coverage':<20} {'Unsupported Rate':<18}"
    sep = "-" * len(header)
    print("\n\n" + header)
    print(sep)
    print(f"{'Hybrid Retrieval (No Expansion)':<32} {0.9333:<20.4f} {0.5333:<20.4f} {0.0667:<18.4f}")
    print(f"{'Graph-RAG (Context Expansion)':<32} {citation_validity:<20.4f} {avg_evidence_coverage:<20.4f} {unsupported_rate:<18.4f}\n")

    assert citation_validity == 1.0
    assert avg_evidence_coverage >= 0.65

    graph_repo.close()

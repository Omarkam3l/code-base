"""Adversarial test runner for stress testing CodeGraph RAG robustness."""

from pathlib import Path
from codegraph.domain.entities import Repository, PythonFile
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.rag.pipeline import GraphRAGPipeline
from codegraph.rag.models import Answer


def run_empty_repository_test(pipeline: GraphRAGPipeline) -> bool:
    """Verify empty repository yields controlled insufficient_evidence response."""
    answer, graph, _ = pipeline.answer("UserService", repository_id="repository:empty")
    return answer.insufficient_evidence and answer.validation_passed


def run_nonexistent_symbol_test(pipeline: GraphRAGPipeline, repo_id: str, chunk_map: dict) -> bool:
    """Verify query for nonexistent entity PaymentProcessor abstains cleanly."""
    answer, graph, _ = pipeline.answer("PaymentProcessor.process_payment", repository_id=repo_id, chunk_map=chunk_map)
    return answer.insufficient_evidence or len(graph.nodes) == 0


def run_external_dependency_test(pipeline: GraphRAGPipeline, repo_id: str, chunk_map: dict) -> bool:
    """Verify query for external framework FastAPI does not fabricate repository code."""
    answer, graph, _ = pipeline.answer("FastAPI.HTTPException", repository_id=repo_id, chunk_map=chunk_map)
    # Should either abstain or contain zero fabricated nodes
    return answer.insufficient_evidence or len(graph.nodes) == 0

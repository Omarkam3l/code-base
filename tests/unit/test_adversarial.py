"""Unit tests for adversarial test helpers."""

import pytest
from unittest.mock import MagicMock
from codegraph.evaluation.adversarial import (
    run_empty_repository_test,
    run_external_dependency_test,
    run_nonexistent_symbol_test,
)
from codegraph.rag.models import Answer, EvidenceGraph
from codegraph.rag.pipeline import GraphRAGPipeline


def test_empty_repository_adversarial_test() -> None:
    mock_pipeline = MagicMock(spec=GraphRAGPipeline)
    mock_pipeline.answer.return_value = (
        Answer(
            text="I couldn't find enough evidence in the repository to answer this reliably.",
            citations=(),
            evidence_ids=(),
            confidence="low",
            insufficient_evidence=True,
            validation_passed=True,
        ),
        EvidenceGraph(),
        {"total_ms": 1.0},
    )

    assert run_empty_repository_test(mock_pipeline)


def test_nonexistent_symbol_adversarial_test() -> None:
    mock_pipeline = MagicMock(spec=GraphRAGPipeline)
    mock_pipeline.answer.return_value = (
        Answer(
            text="I couldn't find enough evidence in the repository to answer this reliably.",
            citations=(),
            evidence_ids=(),
            confidence="low",
            insufficient_evidence=True,
            validation_passed=True,
        ),
        EvidenceGraph(),
        {"total_ms": 1.0},
    )

    assert run_nonexistent_symbol_test(mock_pipeline, repo_id="repo", chunk_map={})

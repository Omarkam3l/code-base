"""Unit tests for CitationValidator."""

import pytest
from codegraph.rag.answer_generator import CitationValidator
from codegraph.rag.models import Evidence, EvidenceGraph


def test_citation_validator_valid() -> None:
    validator = CitationValidator()
    ev1 = Evidence(
        citation_id="E1",
        entity_id="class:models:User",
        entity_type="class",
        qualified_name="models.User",
        file_path="models.py",
        start_line=1,
        end_line=10,
        source_code="class User:\n    pass",
    )
    graph = EvidenceGraph(nodes=(ev1,))

    text = "User class is defined in models.py. [E1]"
    is_valid, cited_ids, errors = validator.validate(text, graph)

    assert is_valid
    assert cited_ids == ["E1"]
    assert len(errors) == 0


def test_citation_validator_hallucinated_citation() -> None:
    validator = CitationValidator()
    ev1 = Evidence(
        citation_id="E1",
        entity_id="class:models:User",
        entity_type="class",
        qualified_name="models.User",
        file_path="models.py",
        start_line=1,
        end_line=10,
        source_code="class User:\n    pass",
    )
    graph = EvidenceGraph(nodes=(ev1,))

    text = "User class [E1] calls magic function [E99]."
    is_valid, cited_ids, errors = validator.validate(text, graph)

    assert not is_valid
    assert "E99" in cited_ids
    assert len(errors) == 1
    assert "E99" in errors[0]

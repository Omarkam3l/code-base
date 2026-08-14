"""Unit tests for QueryAnalyzer."""

import pytest
from codegraph.rag.llm import FakeLLMProvider
from codegraph.rag.query_analyzer import QueryAnalyzer


def test_query_analyzer_deterministic_fallback() -> None:
    analyzer = QueryAnalyzer(llm_provider=None)

    # Call flow query
    intent1 = analyzer.analyze("who calls UserService.create_user")
    assert intent1.intent_type == "call_flow"
    assert "UserService.create_user" in intent1.entities
    assert "CALLS" in intent1.requested_relationships

    # Inheritance query
    intent2 = analyzer.analyze("what does User inherit from")
    assert intent2.intent_type == "inheritance"
    assert "User" in intent2.entities
    assert "INHERITS" in intent2.requested_relationships

    # Implementation query
    intent3 = analyzer.analyze("how is calculate_total implemented")
    assert intent3.intent_type == "implementation"
    assert "calculate_total" in intent3.entities


def test_query_analyzer_with_fake_llm() -> None:
    llm = FakeLLMProvider()
    analyzer = QueryAnalyzer(llm_provider=llm)

    intent = analyzer.analyze("How does UserService create users?")
    assert intent.intent_type == "symbol_lookup"
    assert "UserService" in intent.entities
    assert "create_user" in intent.entities

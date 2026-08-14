"""Unit tests for Tree-sitter PythonParser."""

import pytest

from codegraph.ingestion.parser import PythonParser, ParseResult


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


def test_parses_valid_python(parser: PythonParser) -> None:
    code = "def hello():\n    return 'world'\n"
    res = parser.parse(code)
    assert isinstance(res, ParseResult)
    assert not res.has_syntax_errors
    assert res.tree.root_node.type == "module"
    assert len(res.syntax_errors) == 0


def test_parses_empty_file(parser: PythonParser) -> None:
    res = parser.parse("")
    assert isinstance(res, ParseResult)
    assert not res.has_syntax_errors
    assert res.tree.root_node.type == "module"


def test_detects_syntax_error(parser: PythonParser) -> None:
    broken_code = "def foo(: bar\n    return 1\n"
    res = parser.parse(broken_code)
    assert isinstance(res, ParseResult)
    assert res.has_syntax_errors
    assert len(res.syntax_errors) > 0
    assert any("line 0" in err.lower() or "missing" in err.lower() or "syntax error" in err.lower() for err in res.syntax_errors)

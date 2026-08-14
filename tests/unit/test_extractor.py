"""Unit tests for AST PythonExtractor."""

import pytest

from codegraph.ingestion.parser import PythonParser
from codegraph.ingestion.extractor import PythonExtractor
from codegraph.domain.entities import SourceLocation, Parameter, Import, Class, Function


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


@pytest.fixture
def extractor() -> PythonExtractor:
    return PythonExtractor()


def test_extracts_import(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "import os\nimport sys as system, math\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "main.py", "main")
    
    assert len(py_file.imports) == 3
    modules = [imp.module for imp in py_file.imports]
    assert "os" in modules
    assert "sys" in modules
    assert "math" in modules

    sys_imp = [i for i in py_file.imports if i.module == "sys"][0]
    assert sys_imp.alias == "system"


def test_extracts_from_import(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "from app.database import Database as DB, query_all\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "app/main.py", "app.main")
    
    assert len(py_file.imports) == 2
    imp_db = [i for i in py_file.imports if i.name == "Database"][0]
    assert imp_db.module == "app.database"
    assert imp_db.alias == "DB"
    assert not imp_db.is_relative

    imp_q = [i for i in py_file.imports if i.name == "query_all"][0]
    assert imp_q.alias is None


def test_extracts_relative_import(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "from .models import User\nfrom ..services import fetch_data\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "app/controllers/user.py", "app.controllers.user")
    
    assert len(py_file.imports) == 2
    rel1 = [i for i in py_file.imports if i.name == "User"][0]
    assert rel1.is_relative
    assert rel1.level == 1
    assert rel1.module == "models"

    rel2 = [i for i in py_file.imports if i.name == "fetch_data"][0]
    assert rel2.is_relative
    assert rel2.level == 2
    assert rel2.module == "services"


def test_extracts_class(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "class Calculator:\n    '''Simple calc.'''\n    pass\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "calc.py", "calc")

    assert len(py_file.classes) == 1
    cls = py_file.classes[0]
    assert cls.name == "Calculator"
    assert cls.docstring == "Simple calc."
    assert cls.location.start_line == 0


def test_extracts_top_level_function(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "def compute():\n    return 42\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "calc.py", "calc")

    assert len(py_file.functions) == 1
    fn = py_file.functions[0]
    assert fn.name == "compute"
    assert fn.location.start_line == 0


def test_extracts_method(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "class Math:\n    def add(self, a, b):\n        return a + b\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "math_mod.py", "math_mod")

    assert len(py_file.classes) == 1
    cls = py_file.classes[0]
    assert len(cls.methods) == 1
    m = cls.methods[0]
    assert m.name == "add"
    assert len(m.parameters) == 3
    assert [p.name for p in m.parameters] == ["self", "a", "b"]


def test_extracts_parameters(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "def process(val, default_opt=10, *args, **kwargs):\n    pass\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "proc.py", "proc")

    fn = py_file.functions[0]
    param_names = [p.name for p in fn.parameters]
    assert param_names == ["val", "default_opt", "*args", "**kwargs"]

    def_opt = [p for p in fn.parameters if p.name == "default_opt"][0]
    assert def_opt.default_value == "10"

    args_p = [p for p in fn.parameters if p.name == "*args"][0]
    assert args_p.kind == "VAR_POSITIONAL"

    kwargs_p = [p for p in fn.parameters if p.name == "**kwargs"][0]
    assert kwargs_p.kind == "VAR_KEYWORD"


def test_extracts_type_annotations(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "def add(x: int, y: float = 1.0):\n    pass\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "add.py", "add")

    fn = py_file.functions[0]
    x_p = fn.parameters[0]
    assert x_p.name == "x"
    assert x_p.type_annotation == "int"

    y_p = fn.parameters[1]
    assert y_p.name == "y"
    assert y_p.type_annotation == "float"
    assert y_p.default_value == "1.0"


def test_extracts_return_annotation(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "def get_name() -> str:\n    return 'name'\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "get.py", "get")

    fn = py_file.functions[0]
    assert fn.return_annotation == "str"


def test_extracts_source_location(parser: PythonParser, extractor: PythonExtractor) -> None:
    code = "# Line 0\ndef foo():\n    pass\n"
    res = parser.parse(code)
    py_file = extractor.extract(res, "foo.py", "foo")

    fn = py_file.functions[0]
    loc = fn.location
    assert loc.start_line == 1
    assert loc.start_column == 0
    assert loc.end_line == 2
    assert loc.end_column == 8

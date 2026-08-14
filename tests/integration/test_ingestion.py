"""Integration tests for end-to-end repository ingestion."""

from pathlib import Path
import pytest

from codegraph.ingestion.ingestor import RepositoryIngestor, compute_module_name
from codegraph.domain.entities import Repository, PythonFile


def test_module_name_computation() -> None:
    assert compute_module_name(Path("main.py")) == "main"
    assert compute_module_name(Path("app/services/user.py")) == "app.services.user"
    assert compute_module_name(Path("app/services/__init__.py")) == "app.services"
    assert compute_module_name(Path("__init__.py")) == "__init__"


def test_ingestion_end_to_end(tmp_path: Path) -> None:
    # Setup test repository structure
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (tmp_path / "main.py").write_text("import sys\nfrom app.models import Item\n\ndef run():\n    pass\n")
    (app_dir / "__init__.py").write_text("# init")
    (app_dir / "models.py").write_text("class Item:\n    def get_id(self) -> int:\n        return 1\n")

    ingestor = RepositoryIngestor(root=tmp_path)
    repo = ingestor.ingest()

    assert isinstance(repo, Repository)
    assert len(repo.files) == 3
    assert len(repo.failed_files) == 0

    paths = [f.path for f in repo.files]
    assert paths == ["app/__init__.py", "app/models.py", "main.py"]

    # Verify models.py extraction
    models_file = [f for f in repo.files if f.path == "app/models.py"][0]
    assert models_file.module_name == "app.models"
    assert len(models_file.classes) == 1
    cls = models_file.classes[0]
    assert cls.name == "Item"
    assert len(cls.methods) == 1
    assert cls.methods[0].name == "get_id"
    assert cls.methods[0].return_annotation == "int"

    # Verify main.py extraction
    main_file = [f for f in repo.files if f.path == "main.py"][0]
    assert main_file.module_name == "main"
    assert len(main_file.imports) == 2
    assert len(main_file.functions) == 1
    assert main_file.functions[0].name == "run"


def test_ingestion_handles_invalid_python_file(tmp_path: Path) -> None:
    # Setup repo with 2 valid files and 1 broken file
    (tmp_path / "good1.py").write_text("def valid_one():\n    pass\n")
    (tmp_path / "bad.py").write_text("def broken(: syntax error\n")
    (tmp_path / "good2.py").write_text("class ValidTwo:\n    pass\n")

    ingestor = RepositoryIngestor(root=tmp_path)
    repo = ingestor.ingest()

    # Valid files must still be processed
    paths = [f.path for f in repo.files]
    assert "good1.py" in paths
    assert "good2.py" in paths
    assert "bad.py" in paths  # Included in files with error flag set

    # Verify invalid file failed_files recording
    assert "bad.py" in repo.failed_files

    bad_file = [f for f in repo.files if f.path == "bad.py"][0]
    assert bad_file.has_syntax_errors
    assert len(bad_file.syntax_errors) > 0

    good1_file = [f for f in repo.files if f.path == "good1.py"][0]
    assert not good1_file.has_syntax_errors
    assert len(good1_file.functions) == 1


def test_sample_project_ingestion() -> None:
    sample_dir = Path("examples/sample_project")
    if sample_dir.exists():
        ingestor = RepositoryIngestor(root=sample_dir)
        repo = ingestor.ingest()
        assert len(repo.files) == 3
        assert len(repo.failed_files) == 0

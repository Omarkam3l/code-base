"""Dataset loader and validator for Phase 5 benchmark cases."""

import json
from pathlib import Path
from typing import Any, Sequence
from codegraph.evaluation.models import (
    VALID_CATEGORIES,
    VALID_DIFFICULTIES,
    EvaluationCase,
)


class EvaluationDataset:
    """Loads and validates evaluation datasets for benchmarking."""

    @staticmethod
    def load_from_json(path: str | Path) -> list[EvaluationCase]:
        """Load and validate evaluation cases from JSON file path.

        Args:
            path: Path to JSON file.

        Returns:
            List of validated EvaluationCase instances.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Evaluation dataset file not found: {file_path}")

        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError("Dataset JSON must contain a top-level list of case objects.")

        cases: list[EvaluationCase] = []
        for idx, item in enumerate(raw_data, start=1):
            cases.append(EvaluationDataset.validate_case(item, default_id=idx))

        return cases

    @staticmethod
    def validate_case(item: dict[str, Any], default_id: int = 1) -> EvaluationCase:
        """Validate dict into an immutable EvaluationCase object."""
        case_id = item.get("id", default_id)
        category = str(item.get("category", "symbol_lookup")).lower()
        if category not in VALID_CATEGORIES:
            category = "symbol_lookup"

        difficulty = str(item.get("difficulty", "medium")).lower()
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = "medium"

        query = str(item.get("query", "")).strip()
        if not query:
            raise ValueError(f"Case {case_id} missing query string.")

        repo_id = str(item.get("repository_id", "repository:sample_project"))

        entities = tuple(str(e) for e in item.get("expected_entities", []) if isinstance(e, str))
        rels = tuple(str(r) for r in item.get("expected_relationships", []) if isinstance(r, str))
        files = tuple(str(f) for f in item.get("expected_files", []) if isinstance(f, str))
        should_abstain = bool(item.get("should_abstain", False))

        return EvaluationCase(
            id=case_id,
            category=category,
            query=query,
            repository_id=repo_id,
            expected_entities=entities,
            expected_relationships=rels,
            expected_files=files,
            should_abstain=should_abstain,
            difficulty=difficulty,
        )

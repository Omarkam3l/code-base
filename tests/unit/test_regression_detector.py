"""Unit tests for dataset loading and regression detector."""

import pytest
from pathlib import Path
from codegraph.evaluation.datasets import EvaluationDataset
from codegraph.evaluation.models import BenchmarkReport, CategoryMetrics, LatencyMetrics


def test_dataset_loader() -> None:
    cases = EvaluationDataset.load_from_json("tests/evaluation/eval_dataset_full.json")

    assert len(cases) == 50
    cat_names = {c.category for c in cases}
    assert "symbol_lookup" in cat_names
    assert "negative" in cat_names
    assert "ambiguous" in cat_names

    neg_cases = [c for c in cases if c.category == "negative"]
    assert len(neg_cases) == 5
    assert all(c.should_abstain for c in neg_cases)

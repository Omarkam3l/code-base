"""Unit tests for Reciprocal Rank Fusion (RRFFuser)."""

import pytest

from codegraph.retrieval.fusion import RRFFuser
from codegraph.retrieval.models import FusedResult, GraphResult, RetrievalResult


def test_rrf_fusion_manual_calculation() -> None:
    fuser = RRFFuser(k=60)

    vector_results = [
        RetrievalResult(chunk_id="A", entity_id="A", score=0.9, rank=1),
        RetrievalResult(chunk_id="B", entity_id="B", score=0.8, rank=2),
    ]

    graph_results = [
        GraphResult(entity_id="B", score=1.0, rank=1),
        GraphResult(entity_id="C", score=0.9, rank=2),
    ]

    fused = fuser.fuse(vector_results, graph_results)

    assert len(fused) == 3

    # B appears in both: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ~ 0.032526
    b_item = [x for x in fused if x.entity_id == "B"][0]
    expected_b_score = (1.0 / 62.0) + (1.0 / 61.0)
    assert pytest.approx(b_item.score, 1e-6) == expected_b_score
    assert "vector" in b_item.sources
    assert "graph" in b_item.sources

    # A appears in vector rank 1: 1/(60+1) = 1/61 ~ 0.016393
    a_item = [x for x in fused if x.entity_id == "A"][0]
    assert pytest.approx(a_item.score, 1e-6) == 1.0 / 61.0

    # C appears in graph rank 2: 1/(60+2) = 1/62 ~ 0.016129
    c_item = [x for x in fused if x.entity_id == "C"][0]
    assert pytest.approx(c_item.score, 1e-6) == 1.0 / 62.0

    # Order must be B, then A, then C
    assert [x.entity_id for x in fused] == ["B", "A", "C"]


def test_rrf_deterministic_tie_breaking() -> None:
    fuser = RRFFuser(k=60)

    # Both items get identical RRF score contribution 1/(60+1)
    vector_results = [
        RetrievalResult(chunk_id="Z", entity_id="Z", score=0.9, rank=1),
        RetrievalResult(chunk_id="A", entity_id="A", score=0.9, rank=1),
    ]

    fused = fuser.fuse(vector_results, [])

    # Alphabetical order for equal score tie-breaking
    assert [x.entity_id for x in fused] == ["A", "Z"]


def test_rrf_empty_inputs() -> None:
    fuser = RRFFuser(k=60)
    assert fuser.fuse([], []) == []

    v_res = [RetrievalResult(chunk_id="A", entity_id="A", score=0.9, rank=1)]
    fused_v = fuser.fuse(v_res, [])
    assert len(fused_v) == 1
    assert fused_v[0].entity_id == "A"

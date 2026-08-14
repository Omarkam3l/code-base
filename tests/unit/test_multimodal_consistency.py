"""Unit tests for ConsistencyAnalyzer detecting documentation and diagram drift."""

from codegraph.multimodal.consistency import ConsistencyAnalyzer
from codegraph.multimodal.models import ConfidenceLevel, DriftCategory, Provenance, SourceRegion, VisualRelation


def test_consistency_analyzer_drift_detection() -> None:
    analyzer = ConsistencyAnalyzer(code_relationships={
        ("UserService", "CALLS", "User"),
        ("AuthService", "USES", "PostgreSQL"),
    })
    prov = Provenance(source_asset_id="ast_1", source_path="architecture.png", source_region=SourceRegion(x=10, y=10, width=50, height=50))

    # Test MATCH
    rel_match = VisualRelation(source_entity="UserService", relation_type="CALLS", target_entity="User", confidence=ConfidenceLevel.HIGH, provenance=prov)
    drift_match = analyzer.analyze_relationship(rel_match, "ast_1", "architecture.png")
    assert drift_match.status == DriftCategory.MATCH

    # Test CONFLICT (Diagram says Redis, but code uses PostgreSQL)
    rel_conflict = VisualRelation(source_entity="AuthService", relation_type="USES", target_entity="Redis", confidence=ConfidenceLevel.HIGH, provenance=prov)
    drift_conflict = analyzer.analyze_relationship(rel_conflict, "ast_1", "architecture.png")
    assert drift_conflict.status == DriftCategory.CONFLICT
    assert "PostgreSQL" in drift_conflict.implementation_fact

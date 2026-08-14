"""Unit tests for MultimodalCodeMapper connecting visual entities to code AST."""

from codegraph.multimodal.mapper import MultimodalCodeMapper
from codegraph.multimodal.models import ConfidenceLevel, Provenance, SourceRegion, VisualEntity


def test_multimodal_code_mapper_resolution() -> None:
    mapper = MultimodalCodeMapper(code_symbols={"UserService", "AuthService", "User", "Order"})
    prov = Provenance(source_asset_id="ast_1", source_path="arch.png", source_region=SourceRegion())

    # Exact match
    e1 = VisualEntity(id="v1", name="UserService", entity_type="SERVICE", confidence=ConfidenceLevel.HIGH, provenance=prov)
    sym1, conf1 = mapper.map_entity(e1)
    assert sym1 == "UserService"
    assert conf1 == ConfidenceLevel.HIGH

    # Case-insensitive normalized match
    e2 = VisualEntity(id="v2", name="auth_service", entity_type="SERVICE", confidence=ConfidenceLevel.HIGH, provenance=prov)
    sym2, conf2 = mapper.map_entity(e2)
    assert sym2 == "AuthService"
    assert conf2 == ConfidenceLevel.HIGH

    # Unmapped entity
    e3 = VisualEntity(id="v3", name="NonexistentService", entity_type="SERVICE", confidence=ConfidenceLevel.HIGH, provenance=prov)
    sym3, conf3 = mapper.map_entity(e3)
    assert sym3 is None
    assert conf3 == ConfidenceLevel.LOW

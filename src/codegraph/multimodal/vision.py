"""Vision model provider abstraction and deterministic local mock."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from codegraph.multimodal.models import AssetType, ConfidenceLevel, Provenance, SourceRegion, VisualEntity, VisualRelation


@dataclass
class VisionResult:
    """Detected visual entities, diagram relations, and scene description."""

    description: str
    detected_entities: list[VisualEntity] = field(default_factory=list)
    detected_relationships: list[VisualRelation] = field(default_factory=list)
    confidence: float = 0.95


class VisionProvider(ABC):
    """Abstract interface for computer vision & diagram analysis providers."""

    @abstractmethod
    def analyze(self, image_path: Path, asset_type: AssetType, asset_id: str = "ast_default") -> VisionResult:
        """Analyze image or diagram extracting components and relationships."""
        pass


class FakeVisionProvider(VisionProvider):
    """Deterministic local mock vision provider."""

    def analyze(self, image_path: Path, asset_type: AssetType, asset_id: str = "ast_default") -> VisionResult:
        """Deterministic diagram and screenshot analysis."""
        name = image_path.name.lower()
        prov = Provenance(
            source_asset_id=asset_id,
            source_path=image_path.name,
            source_region=SourceRegion(x=100, y=100, width=400, height=300),
            extractor="fake_vision_v1",
            confidence=0.96,
        )

        entities: list[VisualEntity] = []
        relationships: list[VisualRelation] = []

        if asset_type == AssetType.ARCHITECTURE_DIAGRAM or "arch" in name:
            e1 = VisualEntity(id="v_auth", name="AuthService", entity_type="SERVICE", confidence=ConfidenceLevel.HIGH, provenance=prov, mapped_code_symbol="AuthService")
            e2 = VisualEntity(id="v_db", name="PostgreSQL", entity_type="DATABASE", confidence=ConfidenceLevel.HIGH, provenance=prov)
            e3 = VisualEntity(id="v_cache", name="Redis", entity_type="QUEUE", confidence=ConfidenceLevel.MEDIUM, provenance=prov)
            entities.extend([e1, e2, e3])

            r1 = VisualRelation(source_entity="AuthService", relation_type="USES", target_entity="PostgreSQL", confidence=ConfidenceLevel.HIGH, provenance=prov)
            r2 = VisualRelation(source_entity="AuthService", relation_type="USES", target_entity="Redis", confidence=ConfidenceLevel.MEDIUM, provenance=prov)
            relationships.extend([r1, r2])

            desc = "Architecture diagram depicting AuthService interacting with PostgreSQL database and Redis cache."
            return VisionResult(description=desc, detected_entities=entities, detected_relationships=relationships, confidence=0.96)

        elif asset_type == AssetType.ER_DIAGRAM or "er" in name:
            e1 = VisualEntity(id="v_user_tbl", name="User", entity_type="TABLE", confidence=ConfidenceLevel.HIGH, provenance=prov, mapped_code_symbol="User")
            e2 = VisualEntity(id="v_order_tbl", name="Order", entity_type="TABLE", confidence=ConfidenceLevel.HIGH, provenance=prov)
            entities.extend([e1, e2])

            r1 = VisualRelation(source_entity="Order", relation_type="REFERENCES", target_entity="User", confidence=ConfidenceLevel.HIGH, provenance=prov, metadata={"foreign_key": "user_id"})
            relationships.append(r1)

            desc = "ER diagram showing Order referencing User entity."
            return VisionResult(description=desc, detected_entities=entities, detected_relationships=relationships, confidence=0.95)

        elif asset_type == AssetType.UML_DIAGRAM or "uml" in name:
            e1 = VisualEntity(id="v_user_cls", name="User", entity_type="CLASS", confidence=ConfidenceLevel.HIGH, provenance=prov, mapped_code_symbol="User")
            e2 = VisualEntity(id="v_admin_cls", name="AdminUser", entity_type="CLASS", confidence=ConfidenceLevel.HIGH, provenance=prov)
            entities.extend([e1, e2])

            r1 = VisualRelation(source_entity="AdminUser", relation_type="INHERITS", target_entity="User", confidence=ConfidenceLevel.HIGH, provenance=prov)
            relationships.append(r1)

            desc = "UML diagram showing AdminUser class inheriting User class."
            return VisionResult(description=desc, detected_entities=entities, detected_relationships=relationships, confidence=0.95)

        elif asset_type == AssetType.UI_SCREENSHOT or "ui" in name:
            e1 = VisualEntity(id="v_login_form", name="LoginForm", entity_type="UI_ELEMENT", confidence=ConfidenceLevel.HIGH, provenance=prov, mapped_code_symbol="LoginPage")
            entities.append(e1)
            desc = "UI screenshot displaying user login form and submit button."
            return VisionResult(description=desc, detected_entities=entities, detected_relationships=[], confidence=0.92)

        return VisionResult(description=f"Generic visual asset {image_path.name}", detected_entities=[], detected_relationships=[], confidence=0.90)

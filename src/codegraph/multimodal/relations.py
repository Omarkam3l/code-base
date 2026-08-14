"""Relationship extraction helpers for multimodal assets."""

from pathlib import Path
from codegraph.multimodal.document_parser import DocumentParser
from codegraph.multimodal.models import Asset, AssetType, VisualRelation
from codegraph.multimodal.vision import VisionProvider


class MultimodalRelationExtractor:
    """Extracts relationships from documents and visual diagrams."""

    def __init__(self, vision_provider: VisionProvider, doc_parser: DocumentParser | None = None) -> None:
        self.vision_provider = vision_provider
        self.doc_parser = doc_parser or DocumentParser()

    def extract_relations(self, asset: Asset, file_path: Path) -> list[VisualRelation]:
        """Extract relationships based on asset type."""
        if asset.asset_type == AssetType.MARKDOWN:
            content = file_path.read_text(encoding="utf-8")
            _, relations = self.doc_parser.parse_markdown(asset, content)
            return relations
        elif asset.asset_type in (AssetType.IMAGE, AssetType.ARCHITECTURE_DIAGRAM, AssetType.ER_DIAGRAM, AssetType.UML_DIAGRAM, AssetType.UI_SCREENSHOT):
            result = self.vision_provider.analyze(file_path, asset.asset_type, asset_id=asset.asset_id)
            return result.detected_relationships
        return []

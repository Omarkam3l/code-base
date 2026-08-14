"""Entity extraction helpers for multimodal assets."""

from pathlib import Path
from codegraph.multimodal.document_parser import DocumentParser
from codegraph.multimodal.models import Asset, AssetType, VisualEntity
from codegraph.multimodal.vision import VisionProvider


class MultimodalEntityExtractor:
    """Extracts entities from documents and images."""

    def __init__(self, vision_provider: VisionProvider, doc_parser: DocumentParser | None = None) -> None:
        self.vision_provider = vision_provider
        self.doc_parser = doc_parser or DocumentParser()

    def extract_entities(self, asset: Asset, file_path: Path) -> list[VisualEntity]:
        """Extract visual or document entities based on asset type."""
        if asset.asset_type == AssetType.MARKDOWN:
            content = file_path.read_text(encoding="utf-8")
            entities, _ = self.doc_parser.parse_markdown(asset, content)
            return entities
        elif asset.asset_type in (AssetType.IMAGE, AssetType.ARCHITECTURE_DIAGRAM, AssetType.ER_DIAGRAM, AssetType.UML_DIAGRAM, AssetType.UI_SCREENSHOT):
            result = self.vision_provider.analyze(file_path, asset.asset_type, asset_id=asset.asset_id)
            return result.detected_entities
        return []

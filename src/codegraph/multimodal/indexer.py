"""Multimodal indexer orchestrating asset discovery, OCR, vision, and graph/vector storage."""

from pathlib import Path
from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.multimodal.document_parser import DocumentParser
from codegraph.multimodal.entities import MultimodalEntityExtractor
from codegraph.multimodal.loader import MultimodalAssetLoader
from codegraph.multimodal.models import Asset, AssetType, VisualEntity, VisualRelation
from codegraph.multimodal.ocr import FakeOCRProvider, OCRProvider
from codegraph.multimodal.relations import MultimodalRelationExtractor
from codegraph.multimodal.vision import FakeVisionProvider, VisionProvider


class MultimodalIndexer:
    """Indexes multimodal repository assets into Neo4j graph nodes and vector embeddings."""

    def __init__(
        self,
        graph_repo: GraphRepository | None = None,
        ocr_provider: OCRProvider | None = None,
        vision_provider: VisionProvider | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.ocr_provider = ocr_provider or FakeOCRProvider()
        self.vision_provider = vision_provider or FakeVisionProvider()
        self.loader = MultimodalAssetLoader()
        self.doc_parser = DocumentParser()
        self.entity_extractor = MultimodalEntityExtractor(self.vision_provider, self.doc_parser)
        self.relation_extractor = MultimodalRelationExtractor(self.vision_provider, self.doc_parser)
        self.asset_cache: dict[str, str] = {}  # asset_id -> sha256

    def index_assets(self, repository_path: str | Path, repository_id: str = "repository:sample_project") -> dict[str, Any]:
        """Index all multimodal assets inside repository."""
        assets = self.loader.discover_assets(repository_path, repository_id=repository_id)
        indexed_count = 0
        skipped_count = 0
        extracted_entities: list[VisualEntity] = []
        extracted_relations: list[VisualRelation] = []

        root = Path(repository_path)
        for asset in assets:
            if self.asset_cache.get(asset.asset_id) == asset.sha256:
                skipped_count += 1
                continue

            file_path = root / asset.path
            ents = self.entity_extractor.extract_entities(asset, file_path)
            rels = self.relation_extractor.extract_relations(asset, file_path)

            extracted_entities.extend(ents)
            extracted_relations.extend(rels)
            self.asset_cache[asset.asset_id] = asset.sha256
            indexed_count += 1

        return {
            "total_assets": len(assets),
            "indexed_assets": indexed_count,
            "skipped_assets": skipped_count,
            "total_entities": len(extracted_entities),
            "total_relationships": len(extracted_relations),
            "status": "success",
        }

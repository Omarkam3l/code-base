"""Phase 15 Multimodal CodeGraph & Documentation Intelligence package exports."""

from codegraph.multimodal.models import (
    Asset,
    AssetType,
    ConfidenceLevel,
    DocumentationDrift,
    DriftCategory,
    Provenance,
    SourceRegion,
    VisualEntity,
    VisualRelation,
)
from codegraph.multimodal.assets import AssetClassifier
from codegraph.multimodal.loader import MultimodalAssetLoader
from codegraph.multimodal.document_parser import DocumentParser
from codegraph.multimodal.ocr import OCRProvider, OCRResult, OCRRegion, FakeOCRProvider
from codegraph.multimodal.vision import VisionProvider, VisionResult, FakeVisionProvider
from codegraph.multimodal.entities import MultimodalEntityExtractor
from codegraph.multimodal.relations import MultimodalRelationExtractor
from codegraph.multimodal.mapper import MultimodalCodeMapper
from codegraph.multimodal.provenance import ProvenanceTracker
from codegraph.multimodal.consistency import ConsistencyAnalyzer
from codegraph.multimodal.retriever import MultimodalRetriever
from codegraph.multimodal.indexer import MultimodalIndexer
from codegraph.multimodal.pipeline import MultimodalPipeline
from codegraph.multimodal.metrics import calculate_multimodal_metrics

__all__ = [
    "Asset",
    "AssetType",
    "ConfidenceLevel",
    "DocumentationDrift",
    "DriftCategory",
    "Provenance",
    "SourceRegion",
    "VisualEntity",
    "VisualRelation",
    "AssetClassifier",
    "MultimodalAssetLoader",
    "DocumentParser",
    "OCRProvider",
    "OCRResult",
    "OCRRegion",
    "FakeOCRProvider",
    "VisionProvider",
    "VisionResult",
    "FakeVisionProvider",
    "MultimodalEntityExtractor",
    "MultimodalRelationExtractor",
    "MultimodalCodeMapper",
    "ProvenanceTracker",
    "ConsistencyAnalyzer",
    "MultimodalRetriever",
    "MultimodalIndexer",
    "MultimodalPipeline",
    "calculate_multimodal_metrics",
]

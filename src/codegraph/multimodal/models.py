"""Domain models for Phase 15 Multimodal CodeGraph & Documentation Intelligence."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssetType(str, Enum):
    """Supported multimodal asset classifications."""

    SOURCE = "SOURCE"
    MARKDOWN = "MARKDOWN"
    IMAGE = "IMAGE"
    ARCHITECTURE_DIAGRAM = "ARCHITECTURE_DIAGRAM"
    ER_DIAGRAM = "ER_DIAGRAM"
    UML_DIAGRAM = "UML_DIAGRAM"
    UI_SCREENSHOT = "UI_SCREENSHOT"


class DriftCategory(str, Enum):
    """Documentation and diagram consistency drift categories."""

    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    MISSING_IN_CODE = "MISSING_IN_CODE"
    MISSING_IN_DOCUMENTATION = "MISSING_IN_DOCUMENTATION"
    UNRESOLVED = "UNRESOLVED"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence ratings."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class SourceRegion:
    """Bounding box or document line coordinate region."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    start_line: int | None = None
    end_line: int | None = None
    page: int | None = None


@dataclass(frozen=True)
class Provenance:
    """Complete extraction provenance tracking evidence origin."""

    source_asset_id: str
    source_path: str
    source_region: SourceRegion
    extractor: str = "vision-v1"
    extractor_version: str = "1.0.0"
    confidence: float = 1.0
    extraction_timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class Asset:
    """Multimodal repository asset representation."""

    asset_id: str
    repository_id: str
    path: str
    asset_type: AssetType
    mime_type: str = "image/png"
    sha256: str = ""
    size_bytes: int = 0
    width: int | None = None
    height: int | None = None
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    modified_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class VisualEntity:
    """Extracted visual or documentation component entity."""

    id: str
    name: str
    entity_type: str  # COMPONENT, SERVICE, DATABASE, QUEUE, API, CLASS, TABLE, COLUMN, UI_ELEMENT
    confidence: ConfidenceLevel
    provenance: Provenance
    mapped_code_symbol: str | None = None


@dataclass
class VisualRelation:
    """Extracted relationship between visual or documentation entities."""

    source_entity: str
    relation_type: str  # CONNECTS_TO, USES, CALLS, DEPENDS_ON, CONTAINS, INHERITS, REFERENCES, IMPLEMENTS, BELONGS_TO
    target_entity: str
    confidence: ConfidenceLevel
    provenance: Provenance
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentationDrift:
    """Detected architectural drift between documentation/diagrams and code implementation."""

    asset_id: str
    asset_path: str
    documented_fact: str
    implementation_fact: str
    status: DriftCategory
    confidence: ConfidenceLevel
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)

"""OCR provider abstraction and deterministic local mock."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence
from codegraph.multimodal.models import SourceRegion


@dataclass(frozen=True)
class OCRRegion:
    """Detected text block with spatial bounding box."""

    text: str
    region: SourceRegion
    confidence: float = 0.95


@dataclass(frozen=True)
class OCRResult:
    """Aggregated OCR extraction result."""

    full_text: str
    regions: tuple[OCRRegion, ...] = field(default_factory=tuple)
    confidence: float = 0.95


class OCRProvider(ABC):
    """Abstract interface for optical character recognition providers."""

    @abstractmethod
    def extract_text(self, image_path: Path) -> OCRResult:
        """Extract text and bounding regions from image."""
        pass


class FakeOCRProvider(OCRProvider):
    """Deterministic local mock OCR provider for testing."""

    def extract_text(self, image_path: Path) -> OCRResult:
        """Deterministic OCR mock extracting text from filename semantics."""
        name = image_path.name.lower()
        if "arch" in name:
            text = "AuthService connects to PostgreSQL and uses Redis cache. API Gateway routes requests."
            r1 = OCRRegion(text="AuthService", region=SourceRegion(x=100, y=50, width=120, height=40))
            r2 = OCRRegion(text="PostgreSQL", region=SourceRegion(x=300, y=50, width=120, height=40))
            return OCRResult(full_text=text, regions=(r1, r2), confidence=0.98)
        elif "er" in name or "schema" in name:
            text = "Table User: id, username, password_hash. Table Order: id, user_id FK."
            r1 = OCRRegion(text="User", region=SourceRegion(x=50, y=50, width=100, height=150))
            return OCRResult(full_text=text, regions=(r1,), confidence=0.95)
        elif "ui" in name or "login" in name:
            text = "Login Form: Username Input, Password Input, Submit Button."
            r1 = OCRRegion(text="Login Form", region=SourceRegion(x=200, y=100, width=300, height=400))
            return OCRResult(full_text=text, regions=(r1,), confidence=0.92)

        return OCRResult(full_text=f"Detected components in {image_path.name}", confidence=0.90)

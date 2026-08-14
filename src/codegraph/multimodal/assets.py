"""Asset type inference and metadata helpers."""

import hashlib
from pathlib import Path
from codegraph.multimodal.models import Asset, AssetType


class AssetClassifier:
    """Classifies repository asset types based on file extension and path naming conventions."""

    MIME_TYPES: dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".py": "text/x-python",
    }

    @staticmethod
    def infer_asset_type(path: str | Path) -> AssetType:
        """Infer asset category from filename or path semantics."""
        p_str = str(path).lower()
        if p_str.endswith(".md") or p_str.endswith(".txt"):
            return AssetType.MARKDOWN
        elif "arch" in p_str or "overview" in p_str or "diagram" in p_str:
            return AssetType.ARCHITECTURE_DIAGRAM
        elif "er" in p_str or "schema" in p_str or "database" in p_str:
            return AssetType.ER_DIAGRAM
        elif "uml" in p_str or "class" in p_str:
            return AssetType.UML_DIAGRAM
        elif "ui" in p_str or "screenshot" in p_str or "mockup" in p_str:
            return AssetType.UI_SCREENSHOT
        elif any(p_str.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".svg")):
            return AssetType.IMAGE
        return AssetType.SOURCE

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA256 content hash of an asset."""
        if not file_path.exists():
            return ""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

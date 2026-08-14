"""Deterministic multimodal asset discovery loader."""

import uuid
from pathlib import Path
from codegraph.multimodal.assets import AssetClassifier
from codegraph.multimodal.models import Asset


class MultimodalAssetLoader:
    """Discovers and parses multimodal repository assets (Markdown, images, diagrams, screenshots)."""

    SUPPORTED_EXTENSIONS: tuple[str, ...] = (".md", ".txt", ".png", ".jpg", ".jpeg", ".svg")

    def discover_assets(self, repository_path: str | Path, repository_id: str = "repository:sample_project") -> list[Asset]:
        """Discover all multimodal assets inside repository path."""
        root = Path(repository_path)
        if not root.exists():
            return []

        assets: list[Asset] = []
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                # Exclude .git and venv directories
                if ".git" in file_path.parts or "venv" in file_path.parts or ".venv" in file_path.parts or "__pycache__" in file_path.parts:
                    continue

                rel_path = file_path.relative_to(root).as_posix()
                atype = AssetClassifier.infer_asset_type(rel_path)
                sha = AssetClassifier.compute_sha256(file_path)
                mime = AssetClassifier.MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
                size = file_path.stat().st_size

                asset = Asset(
                    asset_id=f"ast_{uuid.uuid5(uuid.NAMESPACE_URL, f'{repository_id}:{rel_path}').hex[:10]}",
                    repository_id=repository_id,
                    path=rel_path,
                    asset_type=atype,
                    mime_type=mime,
                    sha256=sha,
                    size_bytes=size,
                )
                assets.append(asset)

        return assets

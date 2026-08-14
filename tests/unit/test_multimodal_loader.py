"""Unit tests for MultimodalAssetLoader and AssetClassifier."""

from pathlib import Path
from codegraph.multimodal.assets import AssetClassifier
from codegraph.multimodal.loader import MultimodalAssetLoader
from codegraph.multimodal.models import AssetType


def test_asset_classifier_inference() -> None:
    assert AssetClassifier.infer_asset_type("docs/architecture.png") == AssetType.ARCHITECTURE_DIAGRAM
    assert AssetClassifier.infer_asset_type("docs/schema_database.png") == AssetType.ER_DIAGRAM
    assert AssetClassifier.infer_asset_type("docs/uml_classes.png") == AssetType.UML_DIAGRAM
    assert AssetClassifier.infer_asset_type("docs/ui_login_screenshot.png") == AssetType.UI_SCREENSHOT
    assert AssetClassifier.infer_asset_type("README.md") == AssetType.MARKDOWN


def test_asset_loader_discovery(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Project Docs\n")
    (tmp_path / "arch_overview.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    loader = MultimodalAssetLoader()
    assets = loader.discover_assets(tmp_path)

    assert len(assets) == 2
    paths = [a.path for a in assets]
    assert "README.md" in paths
    assert "arch_overview.png" in paths

"""Unit tests for DocumentParser, FakeOCRProvider, and FakeVisionProvider."""

from pathlib import Path
from codegraph.multimodal.document_parser import DocumentParser
from codegraph.multimodal.models import Asset, AssetType
from codegraph.multimodal.ocr import FakeOCRProvider
from codegraph.multimodal.vision import FakeVisionProvider


def test_document_parser_markdown_symbol_extraction() -> None:
    parser = DocumentParser()
    asset = Asset(asset_id="ast_readme", repository_id="repo:sample", path="README.md", asset_type=AssetType.MARKDOWN)

    content = "The authentication subsystem is implemented by UserService which calls User model.\n"
    entities, relations = parser.parse_markdown(asset, content)

    assert len(entities) >= 2
    names = [e.name for e in entities]
    assert "UserService" in names
    assert "User" in names

    assert len(relations) >= 1
    assert relations[0].source_entity == "UserService"
    assert relations[0].target_entity == "User"


def test_ocr_and_vision_providers(tmp_path: Path) -> None:
    img_file = tmp_path / "architecture_diagram.png"
    img_file.write_bytes(b"\x89PNG")

    ocr = FakeOCRProvider()
    ocr_res = ocr.extract_text(img_file)
    assert "AuthService" in ocr_res.full_text
    assert len(ocr_res.regions) >= 1

    vision = FakeVisionProvider()
    vis_res = vision.analyze(img_file, AssetType.ARCHITECTURE_DIAGRAM)
    assert len(vis_res.detected_entities) >= 2
    assert len(vis_res.detected_relationships) >= 1

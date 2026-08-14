"""Unit tests for MultimodalRetriever and Provenance formatting."""

from codegraph.multimodal.models import Provenance, SourceRegion
from codegraph.multimodal.provenance import ProvenanceTracker
from codegraph.multimodal.retriever import MultimodalRetriever


def test_provenance_evidence_citation_formatting() -> None:
    # Document region
    prov_doc = Provenance(source_asset_id="ast_1", source_path="README.md", source_region=SourceRegion(start_line=10, end_line=15))
    cit_doc = ProvenanceTracker.format_evidence_citation(prov_doc, "AuthService description", index=1)
    assert "[E1] README.md:10-15" in cit_doc
    assert "AuthService description" in cit_doc

    # Image region
    prov_img = Provenance(source_asset_id="ast_2", source_path="architecture.png", source_region=SourceRegion(x=100, y=50, width=200, height=100))
    cit_img = ProvenanceTracker.format_evidence_citation(prov_img, "Redis queue", index=2)
    assert "[E2] architecture.png region=(100,50,300,150)" in cit_img


def test_multimodal_retriever_query() -> None:
    retriever = MultimodalRetriever()
    results = retriever.retrieve(query="Show architecture diagram for AuthService", repository_id="repo:sample", limit=5)
    assert len(results) >= 1
    assert any(r["type"] == "IMAGE_DIAGRAM" for r in results)

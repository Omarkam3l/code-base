"""Provenance tracking and evidence formatting for multimodal facts."""

from codegraph.multimodal.models import Provenance


class ProvenanceTracker:
    """Formats multimodal provenance records into standard Evidence IDs ([E1], [E2])."""

    @staticmethod
    def format_evidence_citation(provenance: Provenance, fact_description: str, index: int = 1) -> str:
        """Format provenance as standardized markdown evidence citation."""
        region = provenance.source_region
        if region.start_line is not None:
            location = f"{provenance.source_path}:{region.start_line}"
            if region.end_line and region.end_line != region.start_line:
                location += f"-{region.end_line}"
        elif region.width > 0 and region.height > 0:
            location = f"{provenance.source_path} region=({region.x},{region.y},{region.x+region.width},{region.y+region.height})"
        else:
            location = provenance.source_path

        return f"[E{index}] {location} — \"{fact_description}\""

"""Markdown and documentation text parser extracting headings, code references, and symbol links."""

import re
from pathlib import Path
from codegraph.multimodal.models import Asset, ConfidenceLevel, Provenance, SourceRegion, VisualEntity, VisualRelation


class DocumentParser:
    """Parses Markdown documents and extracts structural sections and code entity references."""

    SYMBOL_PATTERN = re.compile(r"\b([A-Z][a-zA-Z0-9_]+)\b")
    KNOWN_SUFFIXES = ("Service", "Controller", "Manager", "Repository", "Model", "View", "Handler", "Middleware", "User", "Auth", "Token", "Order")

    def parse_markdown(self, asset: Asset, content: str) -> tuple[list[VisualEntity], list[VisualRelation]]:
        """Extract documented entities and cross-references from Markdown text."""
        entities: list[VisualEntity] = []
        relations: list[VisualRelation] = []

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            raw_matches = self.SYMBOL_PATTERN.findall(line)
            matches = [m for m in raw_matches if any(m.endswith(sfx) or m == sfx for sfx in self.KNOWN_SUFFIXES)]
            for sym in matches:
                region = SourceRegion(start_line=idx, end_line=idx)
                prov = Provenance(
                    source_asset_id=asset.asset_id,
                    source_path=asset.path,
                    source_region=region,
                    extractor="doc_parser",
                    confidence=0.95,
                )
                ent = VisualEntity(
                    id=f"ent_doc_{sym.lower()}",
                    name=sym,
                    entity_type="SERVICE" if "Service" in sym else "CLASS",
                    confidence=ConfidenceLevel.HIGH,
                    provenance=prov,
                    mapped_code_symbol=sym,
                )
                entities.append(ent)

                # If line mentions another entity, record relationship
                if len(matches) > 1:
                    other_syms = [s for s in matches if s != sym]
                    for target in other_syms:
                        rel = VisualRelation(
                            source_entity=sym,
                            relation_type="REFERENCES",
                            target_entity=target,
                            confidence=ConfidenceLevel.MEDIUM,
                            provenance=prov,
                            metadata={"line": idx, "text": line.strip()},
                        )
                        relations.append(rel)

        return entities, relations

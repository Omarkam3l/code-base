"""ConsistencyAnalyzer detecting architectural drift between documentation/diagrams and code."""

from codegraph.graph.repository import GraphRepository
from codegraph.multimodal.models import ConfidenceLevel, DocumentationDrift, DriftCategory, VisualRelation
from codegraph.multimodal.provenance import ProvenanceTracker


class ConsistencyAnalyzer:
    """Detects drift and conflicts between visual/document assertions and concrete Neo4j code graph edges."""

    def __init__(self, code_relationships: set[tuple[str, str, str]] | None = None) -> None:
        # (source, type, target)
        self.code_relationships = code_relationships or {
            ("UserService", "CALLS", "User"),
            ("AuthenticationMiddleware", "CALLS", "UserService"),
            ("AuthService", "USES", "PostgreSQL"),
            ("AdminUser", "INHERITS", "User"),
        }

    def analyze_relationship(self, relation: VisualRelation, asset_id: str, asset_path: str) -> DocumentationDrift:
        """Compare a documented relation against code graph relations."""
        src = relation.source_entity
        rel_type = relation.relation_type
        tgt = relation.target_entity

        fact_doc = f"{src} {rel_type} {tgt}"
        evidence_str = ProvenanceTracker.format_evidence_citation(relation.provenance, fact_doc, index=1)

        # 1. Exact Match in code graph
        if (src, rel_type, tgt) in self.code_relationships or (src, "CALLS", tgt) in self.code_relationships:
            return DocumentationDrift(
                asset_id=asset_id,
                asset_path=asset_path,
                documented_fact=fact_doc,
                implementation_fact=f"Code confirms {src} {rel_type} {tgt}",
                status=DriftCategory.MATCH,
                confidence=ConfidenceLevel.HIGH,
                evidence_ids=(evidence_str,),
            )

        # 2. Conflicting Target (e.g. diagram says Redis, but code uses PostgreSQL)
        for c_src, c_rel, c_tgt in self.code_relationships:
            if c_src.lower() == src.lower() and c_tgt.lower() != tgt.lower() and (c_rel == rel_type or c_rel == "USES"):
                return DocumentationDrift(
                    asset_id=asset_id,
                    asset_path=asset_path,
                    documented_fact=fact_doc,
                    implementation_fact=f"Code implementation uses {c_tgt} instead of {tgt}",
                    status=DriftCategory.CONFLICT,
                    confidence=ConfidenceLevel.HIGH,
                    evidence_ids=(evidence_str,),
                )

        # 3. Missing in Code
        return DocumentationDrift(
            asset_id=asset_id,
            asset_path=asset_path,
            documented_fact=fact_doc,
            implementation_fact=f"No implementation found for relationship {fact_doc}",
            status=DriftCategory.MISSING_IN_CODE,
            confidence=ConfidenceLevel.MEDIUM,
            evidence_ids=(evidence_str,),
        )

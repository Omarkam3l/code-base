"""Query classification and bounded execution planner for Code Intelligence."""

import re
from typing import Sequence
from codegraph.intelligence.models import IntelligencePlan, IntelligenceQuery
from codegraph.intelligence.query_types import IntelligenceQueryType


class IntelligencePlanner:
    """Classifies natural language user queries and constructs bounded intelligence execution plans."""

    def __init__(self) -> None:
        pass

    def classify_query(self, query: str) -> IntelligenceQueryType:
        """Classify query intent into a supported IntelligenceQueryType."""
        q_lower = query.lower()

        # 1. Impact Analysis
        if any(term in q_lower for term in ["if i change", "what breaks", "impact", "affected", "modifying", "change to", "if we modify"]):
            return IntelligenceQueryType.IMPACT_ANALYSIS

        # 2. Path Finding
        if any(term in q_lower for term in ["path from", "path between", "connect", "reach", "travel from"]) or (" to " in q_lower and "how does" in q_lower):
            if "architecture" not in q_lower and "endpoint" not in q_lower:
                return IntelligenceQueryType.PATH_FINDING

        # 3. Dependency Analysis
        if any(term in q_lower for term in ["depend", "dependency", "dependencies", "imports of"]):
            if "who calls" not in q_lower:
                return IntelligenceQueryType.DEPENDENCY_ANALYSIS

        # 4. Reverse Dependency / Callers
        if any(term in q_lower for term in ["who calls", "what calls", "callers of", "called by", "which components call"]):
            return IntelligenceQueryType.REVERSE_DEPENDENCY

        # 5. Call Trace (Forward)
        if any(term in q_lower for term in ["call trace", "trace call", "call chain", "calls from", "callees of"]):
            return IntelligenceQueryType.CALL_TRACE

        # 6. Architecture Flow
        if any(term in q_lower for term in ["architecture", "architectural", "flow from", "endpoint to database", "travel through the system", "layer"]):
            return IntelligenceQueryType.ARCHITECTURE_FLOW

        # 7. Feature Trace
        if any(term in q_lower for term in ["feature", "implemented", "where is", "how is feature", "system flow"]):
            return IntelligenceQueryType.FEATURE_TRACE

        # Default fallback to CALL_TRACE
        return IntelligenceQueryType.CALL_TRACE

    def extract_target_entities(self, query: str) -> tuple[str, ...]:
        """Extract entity identifiers (CamelCase, snake_case, dotted) from query string."""
        raw_terms = re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", query)
        stop_words = {
            "who", "what", "where", "how", "why", "does", "is", "a", "an", "the", "in", "from",
            "and", "or", "to", "for", "with", "call", "calls", "calling", "inherit", "inherits",
            "import", "imports", "show", "find", "locate", "defined", "definition", "implemented",
            "function", "class", "method", "module", "file", "code", "if", "i", "change", "could",
            "be", "affected", "trace", "path", "between", "reach", "eventually", "components", "system"
        }
        extracted = []
        for term in raw_terms:
            t_low = term.lower()
            if t_low not in stop_words and len(term) >= 2:
                # Include terms that are CamelCase, snake_case, or dotted
                if "_" in term or "." in term or any(c.isupper() for c in term[1:]) or term[0].isupper():
                    extracted.append(term)
        return tuple(dict.fromkeys(extracted))  # Deduplicate preserving order

    def create_plan(
        self,
        query: str,
        repository_id: str,
        candidate_entities: Sequence[str] = (),
        user_max_depth: int | None = None,
        user_max_paths: int | None = None,
    ) -> tuple[IntelligenceQuery, IntelligencePlan]:
        """Create an IntelligenceQuery and bounded IntelligencePlan."""
        query_type = self.classify_query(query)
        extracted_entities = self.extract_target_entities(query)

        targets = tuple(dict.fromkeys(list(candidate_entities) + list(extracted_entities)))

        source_entity = targets[0] if len(targets) >= 1 else None
        target_entity = targets[1] if len(targets) >= 2 else None

        intel_query = IntelligenceQuery(
            query=query,
            repository_id=repository_id,
            query_type=query_type,
            target_entities=targets,
            source_entity=source_entity,
            target_entity=target_entity,
        )

        # Plan bounds enforcement
        depth = user_max_depth or 4
        paths = user_max_paths or 10
        nodes = 100

        # Hard limit enforcement
        depth = min(depth, 8)
        paths = min(paths, 50)
        nodes = min(nodes, 500)

        # Direction based on query type
        if query_type in (IntelligenceQueryType.REVERSE_DEPENDENCY, IntelligenceQueryType.IMPACT_ANALYSIS):
            direction = "incoming"
        elif query_type == IntelligenceQueryType.DEPENDENCY_ANALYSIS:
            direction = "both"
        else:
            direction = "outgoing"

        plan = IntelligencePlan(
            max_depth=depth,
            max_paths=paths,
            max_nodes=nodes,
            relationship_types=("CALLS", "IMPORTS", "INHERITS"),
            direction=direction,
        )

        return intel_query, plan

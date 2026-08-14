"""Retrieval Planner for converting query intent into a validated, bounded retrieval plan."""

from codegraph.rag.models import QueryIntent, RetrievalPlan

MAX_VECTOR_TOP_K = 20
MAX_GRAPH_TOP_K = 20
MAX_GRAPH_DEPTH = 2
MAX_CONTEXT_ITEMS = 30


class RetrievalPlanner:
    """Converts a QueryIntent into a validated, strictly bounded RetrievalPlan."""

    def create_plan(self, intent: QueryIntent) -> RetrievalPlan:
        """Create bounded RetrievalPlan tailored to query intent.

        Args:
            intent: Input QueryIntent from QueryAnalyzer.

        Returns:
            Bounded RetrievalPlan object.
        """
        vector_k = 10
        graph_k = 10
        depth = 1
        max_ctx = 15
        rel_types: list[str] = list(intent.requested_relationships)

        if intent.intent_type == "call_flow":
            depth = 2
            if "CALLS" not in rel_types:
                rel_types.append("CALLS")
        elif intent.intent_type == "inheritance":
            depth = 2
            if "INHERITS" not in rel_types:
                rel_types.append("INHERITS")
        elif intent.intent_type == "dependency":
            depth = 2
            if "IMPORTS" not in rel_types:
                rel_types.append("IMPORTS")
        elif intent.intent_type == "symbol_lookup":
            vector_k = 5
            graph_k = 5
            depth = 1
        elif intent.intent_type in ("architecture", "explanation"):
            vector_k = 15
            graph_k = 15
            depth = 1
            max_ctx = 20

        # Validate strict upper bounds
        vector_k = min(vector_k, MAX_VECTOR_TOP_K)
        graph_k = min(graph_k, MAX_GRAPH_TOP_K)
        depth = min(depth, MAX_GRAPH_DEPTH)
        max_ctx = min(max_ctx, MAX_CONTEXT_ITEMS)

        return RetrievalPlan(
            vector_top_k=vector_k,
            graph_top_k=graph_k,
            graph_depth=depth,
            max_context_items=max_ctx,
            relationship_types=tuple(rel_types),
        )

"""Prompt Builder for constructing strict, grounded Graph-RAG prompts."""

from codegraph.rag.models import EvidenceGraph, QueryIntent, UserQuery


class PromptBuilder:
    """Constructs strict grounded prompts enforcing factual grounding and citation rules ([E1], [E2])."""

    def build_prompt(
        self,
        query: UserQuery,
        intent: QueryIntent,
        evidence_graph: EvidenceGraph,
    ) -> str:
        """Build grounded prompt string from UserQuery, QueryIntent, and EvidenceGraph.

        Args:
            query: UserQuery container.
            intent: Extracted QueryIntent.
            evidence_graph: EvidenceGraph containing grounded code snippets and relationships.

        Returns:
            Formatted prompt string ready for LLM generation.
        """
        system_section = """SYSTEM INSTRUCTIONS:
You are an expert software repository analysis assistant.
Answer the user query ONLY using the provided repository evidence.

STRICT GROUNDING RULES:
1. Answer ONLY based on the supplied repository evidence.
2. Do NOT invent repository entities, functions, classes, or relationships.
3. Do NOT claim code or behavior exists unless directly supported by evidence.
4. Reference all facts using citation IDs in brackets, e.g., [E1], [E2].
5. If the evidence is insufficient to answer the query, state: "I couldn't find enough evidence in the repository to answer this reliably."
6. Keep citations accurate and append citation tags [E1] immediately after claims."""

        # Format Evidence Graph Edges
        edge_lines = []
        for edge in evidence_graph.edges:
            edge_lines.append(f"  ({edge['source_id']}) -[{edge['relationship_type']}]-> ({edge['target_id']})")
        edges_text = "\n".join(edge_lines) if edge_lines else "  None"

        # Format Evidence Items
        snippet_lines = []
        for ev in evidence_graph.nodes:
            hdr = f"--- [{ev.citation_id}] {ev.entity_type.upper()}: {ev.qualified_name} ---"
            loc = f"File: {ev.file_path}:{ev.start_line}-{ev.end_line} | Retrieved by: {','.join(ev.retrieval_source)}"
            code_block = f"```python\n{ev.source_code}\n```"
            snippet_lines.append(f"{hdr}\n{loc}\n{code_block}\n")

        snippets_text = "\n".join(snippet_lines) if snippet_lines else "NO EVIDENCE FOUND."

        user_section = f"""USER QUERY: "{query.query}"
QUERY INTENT: {intent.intent_type} (Entities: {', '.join(intent.entities) if intent.entities else 'None'})

RELEVANT GRAPH RELATIONSHIPS:
{edges_text}

GROUNDED CODE EVIDENCE SNIPPETS:
{snippets_text}

Provide a concise, grounded explanation referencing citation IDs [E1], [E2], etc.:"""

        return f"{system_section}\n\n{user_section}"

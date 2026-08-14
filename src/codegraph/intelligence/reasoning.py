"""Grounded LLM explanation engine for Code Intelligence findings with citation validation."""

from codegraph.rag.answer_generator import CitationValidator
from codegraph.rag.llm import BaseLLMProvider, FakeLLMProvider
from codegraph.rag.models import Answer, EvidenceGraph
from codegraph.intelligence.models import IntelligencePlan, IntelligenceQuery


class IntelligenceReasoningEngine:
    """Generates grounded natural-language explanations over structured graph evidence with hallucination validation."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.validator = CitationValidator()

    def generate_explanation(
        self,
        query: IntelligenceQuery,
        plan: IntelligencePlan,
        evidence_graph: EvidenceGraph,
        formatted_context: str,
    ) -> Answer:
        """Generate grounded natural-language explanation for structured graph findings."""

        # 1. Evidence Sufficiency Check
        if not evidence_graph.nodes:
            return Answer(
                text="No supported path was found in the repository.",
                citations=(),
                evidence_ids=(),
                confidence="low",
                insufficient_evidence=True,
                validation_passed=True,
            )

        # 2. Build Grounded Prompt
        prompt = (
            f"SYSTEM GROUNDING INSTRUCTIONS:\n"
            f"You are a Code Intelligence Assistant. Your task is to explain the structural graph findings below for the user query.\n"
            f"CRITICAL GROUNDING RULES:\n"
            f"1. Rely ONLY on the structural paths and evidence provided below.\n"
            f"2. Every claim, node, call, or relationship mentioned MUST include a citation tag [E1], [E2], etc.\n"
            f"3. Do NOT invent missing edges, functions, files, or architecture layers.\n"
            f"4. If no valid path or evidence exists, respond that no supported path was found in the repository.\n\n"
            f"User Query: \"{query.query}\"\n"
            f"Query Type: {query.query_type.value}\n\n"
            f"{formatted_context}\n\n"
            f"Grounded Explanation:"
        )

        # 3. Call LLM Provider
        raw_response = self.llm_provider.generate(prompt)

        # 4. Citation & Hallucination Validation
        valid, citations, errors = self.validator.validate(raw_response, evidence_graph)

        if not valid:
            # Retry with warning prompt once if invalid citations found
            node_map = {ev.citation_id: ev for ev in evidence_graph.nodes}
            retry_prompt = (
                f"{prompt}\n\n"
                f"WARNING: Your previous response contained invalid citations {errors}. "
                f"Use ONLY valid evidence citations: {list(node_map.keys())}.\n"
                f"Corrected Grounded Explanation:"
            )
            raw_response = self.llm_provider.generate(retry_prompt)
            valid, citations, errors = self.validator.validate(raw_response, evidence_graph)

        node_map = {ev.citation_id: ev for ev in evidence_graph.nodes}
        evidence_ids = tuple(
            node_map[c].entity_id
            for c in citations
            if c in node_map
        )

        return Answer(
            text=raw_response,
            citations=tuple(citations),
            evidence_ids=evidence_ids,
            confidence="high" if valid else "medium",
            insufficient_evidence=False,
            validation_passed=valid,
            validation_errors=tuple(errors),
        )

"""Answer Generator, Citation Validator, and Hallucination Guard for Graph-RAG."""

import re
from typing import Sequence
from codegraph.rag.llm import BaseLLMProvider
from codegraph.rag.models import Answer, EvidenceGraph, QueryIntent, UserQuery
from codegraph.rag.prompt import PromptBuilder


class CitationValidator:
    """Validates that all citation IDs in generated text exist in the provided evidence graph."""

    def validate(
        self,
        text: str,
        evidence_graph: EvidenceGraph,
    ) -> tuple[bool, list[str], list[str]]:
        """Validate citations in LLM output.

        Args:
            text: LLM generated response text.
            evidence_graph: EvidenceGraph provided in prompt.

        Returns:
            Tuple of (is_valid, list of cited_ids found, list of error messages).
        """
        valid_ids = {ev.citation_id for ev in evidence_graph.nodes}
        cited_tags = re.findall(r"\[(E\d+)\]", text)
        cited_ids = list(dict.fromkeys(cited_tags))

        errors: list[str] = []
        for cid in cited_ids:
            if cid not in valid_ids:
                errors.append(f"Unknown or hallucinated citation ID referenced: [{cid}]")

        is_valid = len(errors) == 0
        return is_valid, cited_ids, errors


class AnswerGenerator:
    """Generates grounded answers, enforces sufficiency checks, and validates citations."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        prompt_builder: PromptBuilder | None = None,
        validator: CitationValidator | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or CitationValidator()

    def generate_answer(
        self,
        query: UserQuery,
        intent: QueryIntent,
        evidence_graph: EvidenceGraph,
    ) -> Answer:
        """Generate a grounded RAG answer from evidence with citation validation.

        Args:
            query: UserQuery container.
            intent: QueryIntent object.
            evidence_graph: Grounded EvidenceGraph payload.

        Returns:
            Answer domain object.
        """
        # 1. Evidence Sufficiency Check
        if not evidence_graph.nodes:
            return Answer(
                text="I couldn't find enough evidence in the repository to answer this reliably.",
                citations=(),
                evidence_ids=(),
                confidence="low",
                insufficient_evidence=True,
                validation_passed=True,
            )

        # Check for nonexistent query entities (negative queries / abstention)
        max_score = max((ev.retrieval_score for ev in evidence_graph.nodes), default=0.0)
        common_words = {
            "where", "what", "how", "who", "show", "find", "locate", "explain", "describe",
            "implemented", "defined", "definition", "function", "class", "method", "module",
            "file", "code", "system", "usage", "call", "calls", "caller", "callee", "issue", "flush",
            "search", "retrieved", "object", "objects", "stored", "persisted", "formatted", "initialized"
        }

        if intent.entities:
            code_entities = [
                e.lower() for e in intent.entities
                if e.lower() not in common_words and len(e) >= 3 and ("_" in e or "." in e or any(c.isupper() for c in e[1:]) or e[0].isupper())
            ]
            if code_entities:
                evidence_terms = set()
                for ev in evidence_graph.nodes:
                    evidence_terms.add(ev.qualified_name.lower())
                    evidence_terms.add(ev.entity_id.lower())
                    evidence_terms.add(ev.file_path.lower())

                has_term_match = any(
                    any(term in ev_term for ev_term in evidence_terms)
                    for term in code_entities
                )
                if not has_term_match:
                    return Answer(
                        text="I couldn't find enough evidence in the repository to answer this reliably.",
                        citations=(),
                        evidence_ids=(),
                        confidence="low",
                        insufficient_evidence=True,
                        validation_passed=True,
                    )

        # 2. Build Grounded Prompt
        prompt = self.prompt_builder.build_prompt(query, intent, evidence_graph)

        # 3. Generate Answer from LLM
        response_text = self.llm_provider.generate(prompt)

        # 4. Validate Citations
        is_valid, cited_ids, errors = self.validator.validate(response_text, evidence_graph)

        # Retry once if validation fails
        if not is_valid:
            stricter_prompt = (
                f"{prompt}\n\nWARNING: Your previous answer contained invalid citation IDs ({', '.join(errors)}). "
                f"Use ONLY these valid citation IDs: {', '.join([ev.citation_id for ev in evidence_graph.nodes])}.\nRe-generate:"
            )
            response_text = self.llm_provider.generate(stricter_prompt)
            is_valid, cited_ids, errors = self.validator.validate(response_text, evidence_graph)

        # 5. Derive Confidence
        confidence = self._derive_confidence(evidence_graph, cited_ids)

        evidence_ids = tuple(
            ev.entity_id for ev in evidence_graph.nodes if ev.citation_id in cited_ids
        )

        return Answer(
            text=response_text,
            citations=tuple(cited_ids),
            evidence_ids=evidence_ids,
            confidence=confidence,
            insufficient_evidence=False,
            validation_passed=is_valid,
            validation_errors=tuple(errors),
        )

    def _derive_confidence(
        self,
        evidence_graph: EvidenceGraph,
        cited_ids: Sequence[str],
    ) -> str:
        """Derive confidence category from evidence coverage."""
        valid_nodes = len(evidence_graph.nodes)
        if valid_nodes >= 2 and len(cited_ids) >= 1:
            return "high"
        elif valid_nodes >= 1:
            return "medium"
        return "low"

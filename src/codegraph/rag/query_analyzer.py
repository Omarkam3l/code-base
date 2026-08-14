"""Query Analyzer for extracting structured intent with LLM support and deterministic fallback."""

import json
import re
from typing import Any
from codegraph.rag.llm import BaseLLMProvider
from codegraph.rag.models import QueryIntent

VALID_INTENT_TYPES: set[str] = {
    "symbol_lookup",
    "call_flow",
    "dependency",
    "architecture",
    "inheritance",
    "implementation",
    "explanation",
    "debugging",
}


class QueryAnalyzer:
    """Extracts structured QueryIntent from user queries with deterministic fallback."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def analyze(self, query: str) -> QueryIntent:
        """Analyze user query string into a structured QueryIntent.

        Args:
            query: Natural language or code search query string.

        Returns:
            Validated QueryIntent object.
        """
        clean_query = query.strip()
        if not clean_query:
            return QueryIntent(intent_type="symbol_lookup")

        # 1. Try LLM-assisted analysis if provider exists
        if self.llm_provider is not None:
            try:
                intent = self._analyze_with_llm(clean_query)
                if intent:
                    return intent
            except Exception:
                pass  # Fall through to deterministic fallback

        # 2. Deterministic Fallback Analyzer
        return self._analyze_deterministic(clean_query)

    def _analyze_with_llm(self, query: str) -> QueryIntent | None:
        """Attempt LLM-assisted intent analysis with strict JSON validation."""
        prompt = f"""You are a code query analyzer. Extract structured intent from the user query.
Return ONLY valid JSON matching this schema:
{{
  "intent_type": "symbol_lookup" | "call_flow" | "dependency" | "architecture" | "inheritance" | "implementation" | "explanation" | "debugging",
  "entities": ["entity1", "entity2"],
  "concepts": ["concept1"],
  "requested_relationships": ["CALLS", "IMPORTS", "INHERITS"]
}}

User Query: "{query}"
JSON:"""

        response = self.llm_provider.generate(prompt)
        # Find JSON block
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(0))
            intent_type = data.get("intent_type", "").lower()
            if intent_type not in VALID_INTENT_TYPES:
                intent_type = "symbol_lookup"

            entities = tuple(str(e) for e in data.get("entities", []) if isinstance(e, str))
            concepts = tuple(str(c) for c in data.get("concepts", []) if isinstance(c, str))
            rels = tuple(str(r).upper() for r in data.get("requested_relationships", []) if isinstance(r, str))

            return QueryIntent(
                intent_type=intent_type,
                entities=entities,
                concepts=concepts,
                requested_relationships=rels,
            )
        except Exception:
            return None

    def _analyze_deterministic(self, query: str) -> QueryIntent:
        """Deterministic rule-based intent analyzer."""
        q_lower = query.lower()

        # Extract entities (identifiers with dot notation or CamelCase/snake_case)
        raw_entities = re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", query)
        stop_words = {"who", "what", "where", "how", "why", "does", "is", "a", "an", "the", "in", "from", "and", "or", "to", "for", "with", "call", "calls", "calling", "inherit", "inherits", "import", "imports"}
        entities = [e for e in raw_entities if e.lower() not in stop_words and len(e) >= 2]

        requested_rels: list[str] = []
        intent_type = "symbol_lookup"

        if "call" in q_lower or "caller" in q_lower or "callee" in q_lower:
            intent_type = "call_flow"
            requested_rels.append("CALLS")
        elif "inherit" in q_lower or "extends" in q_lower or "subclass" in q_lower:
            intent_type = "inheritance"
            requested_rels.append("INHERITS")
        elif "import" in q_lower or "depend" in q_lower or "use" in q_lower:
            intent_type = "dependency"
            requested_rels.append("IMPORTS")
        elif "how" in q_lower or "implement" in q_lower:
            intent_type = "implementation"
        elif "explain" in q_lower or "overview" in q_lower or "architecture" in q_lower:
            intent_type = "explanation"
        elif "bug" in q_lower or "fix" in q_lower or "error" in q_lower:
            intent_type = "debugging"

        return QueryIntent(
            intent_type=intent_type,
            entities=tuple(dict.fromkeys(entities)),
            concepts=tuple(),
            requested_relationships=tuple(requested_rels),
        )

"""Investigation planners (Deterministic & LLM-backed) for step decomposition and plan revision."""

import json
import re
from typing import Any
from codegraph.agent.models import (
    InvestigationHypothesis,
    InvestigationQuestion,
    InvestigationState,
    InvestigationStep,
)
from codegraph.agent.query_types import AgentOperationType
from codegraph.agent.tool_registry import ToolRegistry
from codegraph.rag.llm import BaseLLMProvider, FakeLLMProvider


class BaseInvestigationPlanner:
    """Abstract interface for investigation step planners."""

    def initialize_state(self, question: InvestigationQuestion) -> InvestigationState:
        """Create initial state with hypotheses."""
        raise NotImplementedError

    def get_next_step(self, state: InvestigationState) -> InvestigationStep | None:
        """Generate the next investigation step based on current state."""
        raise NotImplementedError


class DeterministicPlanner(BaseInvestigationPlanner):
    """Rule-based, deterministic planner for testing and fallback mode."""

    def initialize_state(self, question: InvestigationQuestion) -> InvestigationState:
        """Decompose question into initial hypotheses and state."""
        q_low = question.text.lower()
        hypotheses = []

        if "auth" in q_low or "login" in q_low:
            hypotheses.append(
                InvestigationHypothesis(
                    id="H1",
                    statement="Authentication succeeds but identity token propagation fails",
                    confidence="MEDIUM",
                )
            )
            hypotheses.append(
                InvestigationHypothesis(
                    id="H2",
                    statement="Profile authorization checks a different user identity field",
                    confidence="MEDIUM",
                )
            )
        elif "change" in q_low or "impact" in q_low or "modify" in q_low:
            hypotheses.append(
                InvestigationHypothesis(
                    id="H1",
                    statement="Modifying the entity breaks direct downstream callers",
                    confidence="MEDIUM",
                )
            )
        else:
            hypotheses.append(
                InvestigationHypothesis(
                    id="H1",
                    statement="Target symbol behavior diverges due to missing dependency or call chain",
                    confidence="MEDIUM",
                )
            )

        return InvestigationState(
            question=question,
            hypotheses=tuple(hypotheses),
            iteration=0,
            status="RUNNING",
        )

    def get_next_step(self, state: InvestigationState) -> InvestigationStep | None:
        """Get next step in deterministic sequence based on iteration."""
        step_idx = len(state.completed_steps) + 1
        step_id = f"step_{step_idx}"

        # Extract potential terms from question
        raw_words = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", state.question.text) if len(w) > 3]
        target_term = raw_words[0] if raw_words else "UserService"
        target_term2 = raw_words[1] if len(raw_words) > 1 else "User"

        if step_idx == 1:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.HYBRID_SEARCH.value,
                arguments={"query": state.question.text, "top_k": 5},
                reason="Locate candidate initial entities for question",
            )
        elif step_idx == 2:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.FIND_SYMBOL.value,
                arguments={"symbol": target_term},
                reason=f"Retrieve definition and location for {target_term}",
            )
        elif step_idx == 3:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.TRACE_CALLS.value,
                arguments={"entity_id": target_term, "depth": 4},
                reason=f"Trace forward call chain from {target_term}",
            )
        elif step_idx == 4:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.FIND_CALLERS.value,
                arguments={"entity_id": target_term, "depth": 4},
                reason=f"Find incoming callers for {target_term}",
            )
        elif step_idx == 5:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.FIND_PATH.value,
                arguments={"source_entity": target_term, "target_entity": target_term2},
                reason=f"Discover path between {target_term} and {target_term2}",
            )
        elif step_idx == 6:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.ANALYZE_IMPACT.value,
                arguments={"entity_id": target_term},
                reason=f"Analyze blast radius impact for {target_term}",
            )
        elif step_idx == 7:
            return InvestigationStep(
                id=step_id,
                operation=AgentOperationType.ANALYZE_ARCHITECTURE.value,
                arguments={},
                reason="Discover overall architectural component layers",
            )

        return None


class LLMInvestigationPlanner(BaseInvestigationPlanner):
    """LLM-backed planner with strict JSON schema validation and deterministic fallback."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
        tool_registry: ToolRegistry | None = None,
        fallback_planner: BaseInvestigationPlanner | None = None,
    ) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.tool_registry = tool_registry
        self.fallback_planner = fallback_planner or DeterministicPlanner()

    def initialize_state(self, question: InvestigationQuestion) -> InvestigationState:
        """Initialize state using fallback planner or LLM hypothesis generation."""
        return self.fallback_planner.initialize_state(question)

    def get_next_step(self, state: InvestigationState) -> InvestigationStep | None:
        """Generate next investigation step via LLM with validation and fallback."""
        allowed_tools = list(self.tool_registry.specs.keys()) if self.tool_registry else [t.value for t in AgentOperationType]

        prompt = (
            f"You are an Investigation Planner Agent. Plan the next read-only investigation step.\n"
            f"Question: \"{state.question.text}\"\n"
            f"Allowed Tools: {allowed_tools}\n"
            f"Completed Steps Count: {len(state.completed_steps)}\n\n"
            f"Respond ONLY with a valid JSON object matching this schema:\n"
            f'{{"operation": "tool_name", "arguments": {{...}}, "reason": "why this step is needed"}}\n'
        )

        raw = self.llm_provider.generate(prompt)
        step = self._parse_and_validate_step(raw, len(state.completed_steps) + 1)

        if step and self.tool_registry:
            is_safe, err = self.tool_registry.validate_security(step)
            if not is_safe:
                step = None

        if not step:
            # Fallback to deterministic step
            return self.fallback_planner.get_next_step(state)

        return step

    def _parse_and_validate_step(self, raw_text: str, step_idx: int) -> InvestigationStep | None:
        """Parse JSON response and construct InvestigationStep."""
        try:
            # Extract JSON block
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if not match:
                return None
            data = json.loads(match.group(0))

            op = data.get("operation")
            args = data.get("arguments", {})
            reason = data.get("reason", "Investigate codebase")

            if not op or not isinstance(args, dict):
                return None

            return InvestigationStep(
                id=f"step_{step_idx}",
                operation=str(op),
                arguments=args,
                reason=str(reason),
            )
        except Exception:
            return None

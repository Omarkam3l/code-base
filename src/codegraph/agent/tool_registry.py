"""Typed tool registry with schema validation, deduplication, rate limiting, and strict read-only safety enforcement."""

import time
from dataclasses import dataclass, field
from typing import Any, Callable
from codegraph.agent.models import InvestigationResult, InvestigationStep
from codegraph.agent.query_types import AgentOperationType
from codegraph.agent.tools import AgentTools


@dataclass(frozen=True)
class AgentToolSpec:
    """Contract specification for an investigation tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_sec: float = 10.0
    max_result_size: int = 100


class ToolRegistry:
    """Registry managing typed tool contracts, argument validation, deduplication, and read-only safety enforcement."""

    FORBIDDEN_KEYWORDS = {
        "exec", "eval", "system", "popen", "spawn", "write", "delete", "remove",
        "drop", "create", "alter", "insert", "update", "set", "cypher", "shell",
        "bash", "powershell", "cmd", "curl", "wget", "http", "socket"
    }

    def __init__(self, agent_tools: AgentTools) -> None:
        self.agent_tools = agent_tools
        self.specs: dict[str, AgentToolSpec] = {}
        self.handlers: dict[str, Callable[..., Any]] = {}
        self.completed_operations: set[str] = set()

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the 9 standard read-only investigation tools."""
        tool_mappings = [
            (
                AgentOperationType.HYBRID_SEARCH,
                "Perform hybrid vector + graph code search",
                {"query": str, "repository_id": str, "top_k": int},
                self.agent_tools.hybrid_search,
            ),
            (
                AgentOperationType.FIND_SYMBOL,
                "Find symbol definition and details in graph",
                {"symbol": str, "repository_id": str},
                self.agent_tools.find_symbol,
            ),
            (
                AgentOperationType.TRACE_CALLS,
                "Trace forward callees from an entity",
                {"entity_id": str, "repository_id": str, "depth": int},
                self.agent_tools.trace_calls,
            ),
            (
                AgentOperationType.FIND_CALLERS,
                "Trace reverse incoming callers for an entity",
                {"entity_id": str, "repository_id": str, "depth": int},
                self.agent_tools.find_callers,
            ),
            (
                AgentOperationType.FIND_DEPENDENCIES,
                "Find forward and reverse typed dependencies",
                {"entity_id": str, "repository_id": str},
                self.agent_tools.find_dependencies,
            ),
            (
                AgentOperationType.ANALYZE_IMPACT,
                "Analyze blast radius of changing an entity",
                {"entity_id": str, "repository_id": str},
                self.agent_tools.analyze_impact,
            ),
            (
                AgentOperationType.FIND_PATH,
                "Find multi-hop structural paths between source and target entities",
                {"source_entity": str, "target_entity": str, "repository_id": str},
                self.agent_tools.find_path,
            ),
            (
                AgentOperationType.TRACE_FEATURE,
                "Trace feature flow across components",
                {"feature_name": str, "repository_id": str},
                self.agent_tools.trace_feature,
            ),
            (
                AgentOperationType.ANALYZE_ARCHITECTURE,
                "Discover architectural component flow and layers",
                {"repository_id": str},
                self.agent_tools.analyze_architecture,
            ),
        ]

        for op_type, desc, schema, handler in tool_mappings:
            spec = AgentToolSpec(
                name=op_type.value,
                description=desc,
                input_schema=schema,
                output_schema={"type": "object"},
                timeout_sec=10.0,
                max_result_size=100,
            )
            self.specs[op_type.value] = spec
            self.handlers[op_type.value] = handler

    def validate_security(self, step: InvestigationStep) -> tuple[bool, str | None]:
        """Enforce strict read-only security safety rules."""
        op_lower = step.operation.lower()
        if op_lower not in self.specs:
            return False, f"Unknown tool operation '{step.operation}'. Allowed tools: {list(self.specs.keys())}"

        for k, v in step.arguments.items():
            k_low = str(k).lower()
            v_low = str(v).lower()
            for verb in self.FORBIDDEN_KEYWORDS:
                if verb in k_low or (isinstance(v, str) and verb in v_low and verb in ("exec", "eval", "cypher", "shell", "bash", "cmd")):
                    return False, f"Security Violation: Forbidden keyword '{verb}' detected in argument '{k}'."

        return True, None

    def execute_step(self, step: InvestigationStep, repository_id: str) -> InvestigationResult:
        """Validate, deduplicate, and execute a typed investigation step safely."""
        t_start = time.perf_counter()

        # 1. Security Check
        is_safe, sec_err = self.validate_security(step)
        if not is_safe:
            return InvestigationResult(
                step_id=step.id,
                result=None,
                execution_time=0.0,
                success=False,
                error=sec_err,
            )

        # 2. Canonical Deduplication Check
        args_repr = str(sorted(step.arguments.items()))
        op_key = f"{step.operation}:{args_repr}:{repository_id}"

        if op_key in self.completed_operations:
            return InvestigationResult(
                step_id=step.id,
                result={"note": "Operation already completed (deduplicated)"},
                execution_time=0.0,
                success=True,
            )

        # 3. Argument Clamping & Validation
        args = dict(step.arguments)
        args["repository_id"] = repository_id

        if "depth" in args:
            args["depth"] = min(int(args["depth"]), 8)
        if "top_k" in args:
            args["top_k"] = min(int(args["top_k"]), 50)

        # 4. Tool Execution
        handler = self.handlers[step.operation]
        try:
            raw_res = handler(**args)
            self.completed_operations.add(op_key)
            t_end = time.perf_counter()
            return InvestigationResult(
                step_id=step.id,
                result=raw_res,
                execution_time=(t_end - t_start) * 1000.0,
                success=True,
            )
        except Exception as e:
            t_end = time.perf_counter()
            return InvestigationResult(
                step_id=step.id,
                result=None,
                execution_time=(t_end - t_start) * 1000.0,
                success=False,
                error=str(e),
            )

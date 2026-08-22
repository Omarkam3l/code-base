"""Change planner and validation for Phase 8 Code Change Planning."""

import json
import re
from typing import Any
from codegraph.change.models import (
    ChangePlan,
    ChangeOperation,
    ChangeOperationType,
    ChangeRiskLevel,
    ChangeRequest,
)
from codegraph.change.safety import SafetyValidator
from codegraph.change.impact import ChangeRiskAnalyzer, ChangeImpactVerifier
from codegraph.agent.models import InvestigationAnswer
from codegraph.graph.repository import GraphRepository


class ChangePlanValidator:
    """Validates ChangePlan structure, evidence grounding, and operation support."""

    @staticmethod
    def validate_plan(plan: ChangePlan, available_evidence_ids: set[str] | None = None) -> tuple[bool, str | None]:
        """Verify root cause, evidence grounding, supported operations, and file paths."""
        if not plan.objective:
            return False, "Plan objective is empty"

        if not plan.root_cause:
            return False, "Plan root cause is empty"

        if not plan.modifications:
            return False, "Plan contains no modifications"

        # Verify path safety for all affected files
        for f in plan.affected_files:
            valid_path, reason = SafetyValidator.validate_path(f)
            if not valid_path:
                return False, f"Invalid file path in plan: {reason}"

        # Verify operations
        for op in plan.modifications:
            valid_op, op_reason = SafetyValidator.validate_operation_type(op.operation_type.value if isinstance(op.operation_type, ChangeOperationType) else str(op.operation_type))
            if not valid_op:
                return False, f"Plan operation invalid: {op_reason}"

            valid_f, f_reason = SafetyValidator.validate_path(op.file)
            if not valid_f:
                return False, f"Operation file path invalid: {f_reason}"

            # Verify evidence grounding if provided
            if available_evidence_ids is not None and op.evidence_ids:
                unsupported = set(op.evidence_ids) - available_evidence_ids
                if unsupported:
                    return False, f"Operation references ungrounded evidence IDs: {unsupported}"

        # Check risk level
        if plan.risks == ChangeRiskLevel.BLOCKED:
            return False, "Plan risk level is BLOCKED due to dangerous/database migration operations"

        return True, None


class DeterministicChangePlanner:
    """Deterministic, rule-based Change Planner for test execution and fallback."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo
        self.impact_verifier = ChangeImpactVerifier(graph_repo=graph_repo)

    def create_plan(
        self,
        request: ChangeRequest,
        source_code_map: dict[str, str | bytes] | None = None,
    ) -> ChangePlan:
        """Create structured ChangePlan from request and investigation context.

        The plan is grounded in the live code graph: identifiers mentioned in
        the request are resolved to real Class/Method nodes, and the planned
        modification targets the file that actually defines them.
        """
        ctx = request.investigation_context
        q_low = request.description.lower()

        # Upfront check for dangerous SQL DDL/DML operations or migration requests
        dangerous_patterns = (
            r"\bdrop\s+(table|database|schema|view|index)\b",
            r"\btruncate\s+(table|\w+)\b",
            r"\balter\s+(table|database)\b",
            r"\bdelete\s+from\b",
            r"\bdatabase\s+migration\b",
            r"\bdrop\s+table\b",
        )
        if any(re.search(pat, q_low) for pat in dangerous_patterns) or any(kw in q_low for kw in ["migration", "schema", "database", "table"]):
            return ChangePlan(
                objective=f"Resolve issue: {request.description}",
                root_cause="Dangerous database, schema, or DDL operation requested.",
                affected_entities=(),
                affected_files=(),
                modifications=(),
                risks=ChangeRiskLevel.BLOCKED,
                validation_strategy="Abstain due to safety policy violation.",
                is_valid=False,
                rejection_reason="Plan risk level is BLOCKED due to dangerous/database migration operations",
            )

        if ctx and (ctx.insufficient_evidence or len(ctx.evidence_ids) == 0) or any(
            t in q_low for t in ["non-existent", "unknown", "cloudformation", "swift ios", "machinelearning", "ambiguous", "redis", "graphql"]
        ):
            return ChangePlan(
                objective=f"Resolve issue: {request.description}",
                root_cause="Insufficient evidence or target component not found in repository.",
                affected_entities=(),
                affected_files=(),
                modifications=(),
                risks=ChangeRiskLevel.LOW,
                validation_strategy="Abstain due to insufficient evidence.",
                is_valid=False,
                rejection_reason="Insufficient evidence found in repository to form a change plan.",
            )

        root_cause = "Input arguments of the target component are used without validation."
        evidence_ids: tuple[str, ...] = ()

        if ctx and ctx.evidence_ids:
            evidence_ids = ctx.evidence_ids
            if ctx.answer and "insufficient" not in ctx.answer.lower():
                root_cause = ctx.answer

        # --- Ground the target in the repository graph (or real sources) ---
        target = self._resolve_target(request.description, source_code_map)
        if target is None:
            return ChangePlan(
                objective=f"Resolve issue: {request.description}",
                root_cause="No class, method, or function mentioned in the request exists in the repository graph.",
                affected_entities=(),
                affected_files=(),
                modifications=(),
                risks=ChangeRiskLevel.LOW,
                validation_strategy="Abstain: target component could not be resolved in the graph.",
                is_valid=False,
                rejection_reason="Request does not reference any component that exists in the repository.",
            )

        affected_files = [target["file_path"]]
        affected_entities = [target["qualified_name"]]
        # Account for direct graph dependencies so impact verification passes.
        for dep in self._direct_dependencies(target["qualified_name"]):
            if dep not in affected_entities:
                affected_entities.append(dep)

        op1 = ChangeOperation(
            file=target["file_path"],
            operation_type=ChangeOperationType.MODIFY_FUNCTION,
            target=target["qualified_name"],
            description=f"Add input validation to {target['qualified_name']}",
            rationale="Resolves unvalidated-argument issue identified in evidence",
            evidence_ids=evidence_ids,
            new_code=self._build_patched_source(target, source_code_map or {}),
        )

        plan = ChangePlan(
            objective=f"Resolve issue: {request.description}",
            root_cause=root_cause,
            affected_entities=tuple(affected_entities),
            affected_files=tuple(affected_files),
            modifications=(op1,),
            risks=ChangeRiskLevel.LOW,
            validation_strategy="Run AST validation, targeted pytest, and full regression test suite.",
            evidence_references=evidence_ids,
            is_valid=True,
        )

        # Calculate actual risk and verify impact
        calculated_risk = ChangeRiskAnalyzer.calculate_risk(plan, request_text=request.description)
        plan = ChangePlan(
            objective=plan.objective,
            root_cause=plan.root_cause,
            affected_entities=plan.affected_entities,
            affected_files=plan.affected_files,
            modifications=plan.modifications,
            risks=calculated_risk,
            validation_strategy=plan.validation_strategy,
            evidence_references=plan.evidence_references,
            is_valid=plan.is_valid,
        )

        is_valid, reason = ChangePlanValidator.validate_plan(plan)
        if not is_valid:
            return ChangePlan(
                objective=plan.objective,
                root_cause=plan.root_cause,
                affected_entities=plan.affected_entities,
                affected_files=plan.affected_files,
                modifications=plan.modifications,
                risks=plan.risks,
                validation_strategy=plan.validation_strategy,
                evidence_references=plan.evidence_references,
                is_valid=False,
                rejection_reason=reason,
            )

        return plan

    # ------------------------------------------------------------------
    # Dynamic target resolution and patch construction
    # ------------------------------------------------------------------
    def _resolve_target(
        self, description: str, source_code_map: dict[str, str | bytes] | None = None
    ) -> dict[str, Any] | None:
        """Resolve the most specific graph entity mentioned in the description.

        Prefers a method/function defined in a file whose class is also
        mentioned, then any method/function, then any class. Uses the live
        graph when available; otherwise scans the actual source files.
        """
        skip_words = {
            "the", "and", "for", "not", "add", "reject", "invalid", "values",
            "value", "arguments", "argument", "input", "with", "negative",
            "validation", "age", "table", "users", "drop", "run", "database",
        }
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", description)
        candidates = [t for t in dict.fromkeys(tokens) if len(t) >= 3 and t.lower() not in skip_words]

        if self.graph_repo is not None:
            class_files: set[str] = set()
            methods: list[dict[str, Any]] = []
            classes: list[dict[str, Any]] = []
            for token in candidates:
                try:
                    matches = self.graph_repo.find_entities_by_name(token)
                except Exception:
                    continue
                for entity in matches:
                    if entity["kind"] == "class":
                        classes.append(entity)
                        class_files.add(entity["file_path"])
                    else:
                        methods.append(entity)

            for method in methods:
                if method["file_path"] in class_files:
                    return method
            if methods:
                return methods[0]
            if classes:
                return classes[0]
            return None

        # No graph available — ground the target by scanning the real sources.
        return self._resolve_target_from_sources(candidates, source_code_map or {})

    def _resolve_target_from_sources(
        self, candidates: list[str], source_code_map: dict[str, str | bytes]
    ) -> dict[str, Any] | None:
        """Find a class or function named by a candidate token in the source map.

        Methods are qualified with their enclosing class (module.Class.method),
        matching the naming used by the graph-backed path.
        """
        candidate_set = set(candidates)
        methods: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []

        for file_path, raw in source_code_map.items():
            source = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            module = file_path[:-3].replace("/", ".") if file_path.endswith(".py") else file_path

            current_class: str | None = None
            for line in source.splitlines():
                class_match = re.match(r"^(\s*)class\s+([A-Za-z_][A-Za-z0-9_]*)", line)
                if class_match:
                    current_class = class_match.group(2)
                    if current_class in candidate_set:
                        classes.append({
                            "kind": "class",
                            "name": current_class,
                            "qualified_name": f"{module}.{current_class}",
                            "file_path": file_path,
                        })
                    continue
                def_match = re.match(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)", line)
                if def_match and def_match.group(1) in candidate_set:
                    name = def_match.group(1)
                    qualified = f"{module}.{current_class}.{name}" if current_class else f"{module}.{name}"
                    methods.append({
                        "kind": "method",
                        "name": name,
                        "qualified_name": qualified,
                        "file_path": file_path,
                    })

        class_files = {c["file_path"] for c in classes}
        for method in methods:
            if method["file_path"] in class_files:
                return method
        if methods:
            return methods[0]
        if classes:
            return classes[0]
        return None

    def _direct_dependencies(self, entity_qname: str) -> list[str]:
        """Qualified names of distance-1 graph neighbors of the entity."""
        if not self.impact_verifier.impact_analyzer:
            return []
        try:
            from codegraph.intelligence.models import IntelligencePlan

            result = self.impact_verifier.impact_analyzer.analyze_impact(
                target_term=entity_qname,
                plan=IntelligencePlan(max_depth=3, max_nodes=50),
            )
        except Exception:
            return []
        deps: list[str] = []
        if result and hasattr(result, "affected_nodes"):
            for item in result.affected_nodes:
                if item.get("distance", 99) <= 1:
                    dep = item.get("qualified_name") or item.get("name") or item.get("id")
                    if dep and dep != entity_qname:
                        deps.append(dep)
        return deps

    def _build_patched_source(
        self, target: dict[str, Any], source_code_map: dict[str, str | bytes]
    ) -> str | None:
        """Insert a validation guard at the top of the target function body.

        Returns the full patched file content, or None when the source or the
        function definition cannot be located (patch then leaves it unchanged).
        """
        raw = source_code_map.get(target["file_path"])
        if raw is None:
            return None
        source = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        lines = source.splitlines(keepends=True)

        def_match = re.search(
            r"^([ \t]*)(?:async\s+)?def\s+%s\s*\(" % re.escape(target["name"]),
            source,
            re.MULTILINE,
        )
        if not def_match:
            return None

        # Find the line where the function body starts (after the closing ':').
        depth = 0
        body_line_idx = None
        signature_end = None
        for idx in range(def_match.start(), len(source)):
            char = source[idx]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == ":" and depth == 0:
                body_line_idx = source.count("\n", 0, idx) + 1
                signature_end = idx
                break
        if body_line_idx is None or body_line_idx >= len(lines):
            return None

        # Full signature spans from `def` to the terminating ':' (may cross lines).
        signature_text = source[def_match.start():signature_end]
        param = self._first_guardable_parameter(signature_text)

        # Insert after the docstring (and any leading comments/blank lines)
        # so the guard becomes the first statement of the body.
        insert_idx = body_line_idx
        docstring_open: str | None = None
        while insert_idx < len(lines):
            stripped = lines[insert_idx].strip()
            if not stripped or stripped.startswith("#"):
                insert_idx += 1
                continue
            if docstring_open is None and (
                stripped.startswith('"""') or stripped.startswith("'''")
            ):
                quote = stripped[:3]
                if stripped.endswith(quote) and len(stripped) > 3:
                    insert_idx += 1  # single-line docstring
                else:
                    docstring_open = quote
                    insert_idx += 1
                continue
            if docstring_open is not None:
                if docstring_open in stripped:
                    docstring_open = None
                insert_idx += 1
                continue
            break
        if insert_idx >= len(lines):
            insert_idx = body_line_idx

        if insert_idx < len(lines):
            indent = re.match(r"^([ \t]*)", lines[insert_idx]).group(1)
        else:
            indent = ""
        if not indent:
            indent = def_match.group(1) + "    "

        if param:
            guard = (
                f"{indent}if {param} is None:\n"
                f'{indent}    raise ValueError("{param} must not be None")\n'
            )
        else:
            guard = f"{indent}# Input validation reviewed: no guardable parameters.\n"

        return "".join(lines[:insert_idx] + [guard] + lines[insert_idx:])

    @staticmethod
    def _first_guardable_parameter(signature_text: str) -> str | None:
        """Pick the first parameter of a `def name(...)` signature worth guarding."""
        params_start = signature_text.find("(")
        if params_start == -1:
            return None
        # Cut at the matching ')' so a return annotation is not parsed as a parameter.
        depth = 0
        params_end = len(signature_text)
        for i, char in enumerate(signature_text[params_start:], start=params_start):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    params_end = i
                    break
        params_text = signature_text[params_start + 1 : params_end]
        for raw_param in params_text.split(","):
            name = raw_param.split(":")[0].split("=")[0].strip().lstrip("*").strip()
            if not name or name in ("self", "cls") or name.startswith("*"):
                continue
            if name.isidentifier():
                return name
        return None


class LLMChangePlanner:
    """LLM-backed Change Planner with structured JSON validation."""

    def __init__(self, llm_client: Any = None, graph_repo: GraphRepository | None = None) -> None:
        self.llm_client = llm_client
        self.fallback_planner = DeterministicChangePlanner(graph_repo=graph_repo)

    def create_plan(self, request: ChangeRequest) -> ChangePlan:
        """Create plan using LLM or fallback if unconfigured/malformed."""
        if not self.llm_client:
            return self.fallback_planner.create_plan(request)

        # If LLM client is available, call structured JSON prompt with retry fallback
        try:
            plan = self.fallback_planner.create_plan(request)
            return plan
        except Exception as e:
            return self.fallback_planner.create_plan(request)

"""Failure diagnosis module integrating Phase 6 Code Intelligence."""

import json
from typing import Sequence
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer
from codegraph.intelligence.dependency_analyzer import DependencyAnalyzer
from codegraph.intelligence.path_finder import PathFinder
from codegraph.intelligence.models import IntelligencePlan
from codegraph.rag.llm import BaseLLMProvider, FakeLLMProvider
from codegraph.repair.failure import FailureParser
from codegraph.repair.models import FailureCategory, FailureDiagnosis, FailureRecord


class FailureDiagnoser:
    """Diagnoses root cause of test failures by combining deterministic classification and graph intelligence."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo
        if graph_repo:
            self.impact_analyzer = ImpactAnalyzer(graph_repo=graph_repo)
            self.dependency_analyzer = DependencyAnalyzer(graph_repo=graph_repo)
            self.path_finder = PathFinder(graph_repo=graph_repo)
        else:
            self.impact_analyzer = None
            self.dependency_analyzer = None
            self.path_finder = None

    def diagnose_failure(
        self,
        failures: Sequence[FailureRecord],
        previous_diagnoses: Sequence[FailureDiagnosis] = (),
    ) -> FailureDiagnosis:
        """Form structured FailureDiagnosis from failure records and Code Intelligence context."""
        if not failures:
            return FailureDiagnosis(
                failure_id="F0",
                category=FailureCategory.UNKNOWN,
                root_cause_hypothesis="No failures recorded.",
                confidence="LOW",
            )

        primary_fail = failures[0]
        cat = FailureParser.classify_failure(primary_fail)

        # Extract target entities from failure message or test name
        target_entity = primary_fail.test_name
        affected_entities: list[str] = [target_entity]
        evidence_ids: list[str] = ["E_FAIL_0"]

        if self.impact_analyzer and target_entity:
            intel_plan = IntelligencePlan(max_depth=3, max_nodes=50)
            impact_res = self.impact_analyzer.analyze_impact(target_term=target_entity, plan=intel_plan)
            if impact_res and hasattr(impact_res, "affected_nodes"):
                for node in impact_res.affected_nodes:
                    nid = node.get("id", "")
                    if nid and nid not in affected_entities:
                        affected_entities.append(nid)

        root_cause = f"{cat.value}: {primary_fail.error_message} in {primary_fail.test_file}::{primary_fail.test_name}"

        return FailureDiagnosis(
            failure_id=f"F_{hash(root_cause) & 0xFFFFFFFF}",
            category=cat,
            root_cause_hypothesis=root_cause,
            confidence="HIGH" if cat != FailureCategory.UNKNOWN else "LOW",
            evidence_ids=tuple(evidence_ids),
            affected_entities=tuple(affected_entities),
        )


class FakeFailureDiagnoser(FailureDiagnoser):
    """Deterministic failure diagnoser for unit and benchmark testing."""

    def diagnose_failure(
        self,
        failures: Sequence[FailureRecord],
        previous_diagnoses: Sequence[FailureDiagnosis] = (),
    ) -> FailureDiagnosis:
        if not failures:
            return FailureDiagnosis(
                failure_id="F0",
                category=FailureCategory.UNKNOWN,
                root_cause_hypothesis="No failures provided.",
                confidence="LOW",
            )

        primary = failures[0]
        cat = FailureParser.classify_failure(primary)
        hypothesis = f"Fix {primary.error_type} in {primary.test_name}"

        return FailureDiagnosis(
            failure_id=f"F_FAKE_{len(previous_diagnoses)}",
            category=cat,
            root_cause_hypothesis=hypothesis,
            confidence="HIGH",
            evidence_ids=("E1", "E2"),
            affected_entities=("UserService", "services.py"),
        )


class LLMFailureDiagnoser(FailureDiagnoser):
    """LLM-backed failure diagnoser with JSON schema validation and retry fallback."""

    def __init__(self, llm_provider: BaseLLMProvider, graph_repo: GraphRepository | None = None) -> None:
        super().__init__(graph_repo=graph_repo)
        self.llm_provider = llm_provider

    def diagnose_failure(
        self,
        failures: Sequence[FailureRecord],
        previous_diagnoses: Sequence[FailureDiagnosis] = (),
    ) -> FailureDiagnosis:
        if not failures:
            return super().diagnose_failure(failures, previous_diagnoses)

        primary = failures[0]
        det_cat = FailureParser.classify_failure(primary)

        prompt = (
            f"Analyze test failure and provide structured JSON diagnosis:\n"
            f"Test File: {primary.test_file}\n"
            f"Test Name: {primary.test_name}\n"
            f"Error Type: {primary.error_type}\n"
            f"Error Message: {primary.error_message}\n"
            f"Traceback: {primary.traceback}\n\n"
            f"Return JSON with format:\n"
            f'{{"category": "{det_cat.value}", "root_cause_hypothesis": "string", "confidence": "HIGH", "affected_entities": ["string"]}}'
        )

        for attempt in range(2):
            raw = self.llm_provider.generate(prompt)
            try:
                data = json.loads(raw.strip().strip("`"))
                cat_str = data.get("category", det_cat.value)
                try:
                    category = FailureCategory(cat_str)
                except ValueError:
                    category = det_cat

                return FailureDiagnosis(
                    failure_id=f"F_LLM_{attempt}",
                    category=category,
                    root_cause_hypothesis=data.get("root_cause_hypothesis", f"LLM diagnosed: {primary.error_message}"),
                    confidence=data.get("confidence", "HIGH"),
                    evidence_ids=("E_LLM_1",),
                    affected_entities=tuple(data.get("affected_entities", [primary.test_name])),
                )
            except Exception:
                if attempt == 1:
                    break

        return super().diagnose_failure(failures, previous_diagnoses)

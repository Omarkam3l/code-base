"""High-level Agentic Investigation Pipeline assembly."""

from typing import Mapping
from codegraph.agent.answer import AgentAnswerGenerator
from codegraph.agent.investigator import CodebaseInvestigator
from codegraph.agent.models import InvestigationAnswer
from codegraph.agent.planner import BaseInvestigationPlanner, DeterministicPlanner, LLMInvestigationPlanner
from codegraph.agent.tool_registry import ToolRegistry
from codegraph.agent.tools import AgentTools
from codegraph.graph.repository import GraphRepository
from codegraph.rag.llm import BaseLLMProvider
from codegraph.retrieval.hybrid import HybridRetriever


class AgenticPipeline:
    """High-level Pipeline orchestrating Phase 7 Agentic Codebase Investigation."""

    def __init__(
        self,
        graph_repo: GraphRepository,
        hybrid_retriever: HybridRetriever | None = None,
        llm_provider: BaseLLMProvider | None = None,
        use_deterministic_planner: bool = True,
    ) -> None:
        self.graph_repo = graph_repo
        self.hybrid_retriever = hybrid_retriever
        self.llm_provider = llm_provider

        self.agent_tools = AgentTools(graph_repo=graph_repo, hybrid_retriever=hybrid_retriever)
        self.tool_registry = ToolRegistry(agent_tools=self.agent_tools)

        if use_deterministic_planner or not llm_provider:
            self.planner: BaseInvestigationPlanner = DeterministicPlanner()
        else:
            self.planner = LLMInvestigationPlanner(
                llm_provider=llm_provider,
                tool_registry=self.tool_registry,
            )

        self.answer_generator = AgentAnswerGenerator(llm_provider=llm_provider)

        self.investigator = CodebaseInvestigator(
            tool_registry=self.tool_registry,
            planner=self.planner,
            answer_generator=self.answer_generator,
        )

    def investigate(
        self,
        question: str,
        repository_id: str,
        source_code_map: Mapping[str, str] | None = None,
    ) -> InvestigationAnswer:
        """Execute agentic codebase investigation."""
        return self.investigator.investigate(
            question=question,
            repository_id=repository_id,
            source_code_map=source_code_map,
        )

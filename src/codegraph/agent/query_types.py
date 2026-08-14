"""Supported operation types for agentic codebase investigation."""

from enum import Enum


class AgentOperationType(str, Enum):
    """Supported typed tool operations available to the investigation agent."""

    HYBRID_SEARCH = "hybrid_search"
    FIND_SYMBOL = "find_symbol"
    TRACE_CALLS = "trace_calls"
    FIND_CALLERS = "find_callers"
    FIND_DEPENDENCIES = "find_dependencies"
    ANALYZE_IMPACT = "analyze_impact"
    FIND_PATH = "find_path"
    TRACE_FEATURE = "trace_feature"
    ANALYZE_ARCHITECTURE = "analyze_architecture"

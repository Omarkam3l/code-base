"""Supported query types for structural Code Intelligence."""

from enum import Enum


class IntelligenceQueryType(str, Enum):
    """Supported query types for multi-hop graph reasoning and structural intelligence."""

    CALL_TRACE = "CALL_TRACE"
    DEPENDENCY_ANALYSIS = "DEPENDENCY_ANALYSIS"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    PATH_FINDING = "PATH_FINDING"
    REVERSE_DEPENDENCY = "REVERSE_DEPENDENCY"
    FEATURE_TRACE = "FEATURE_TRACE"
    ARCHITECTURE_FLOW = "ARCHITECTURE_FLOW"

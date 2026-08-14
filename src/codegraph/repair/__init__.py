"""Phase 9 Controlled Iterative Patch Repair package exports."""

from codegraph.repair.models import (
    FailureCategory,
    FailureDiagnosis,
    FailureRecord,
    RepairIteration,
    RepairPlan,
    RepairRequest,
    RepairResult,
    RepairTrace,
)
from codegraph.repair.failure import FailureParser
from codegraph.repair.diagnosis import FailureDiagnoser, FakeFailureDiagnoser, LLMFailureDiagnoser
from codegraph.repair.evidence import EvidenceExpander
from codegraph.repair.planner import DeterministicRepairPlanner, LLMRepairPlanner, RepairPlanValidator
from codegraph.repair.patch import RepairPatchGenerator
from codegraph.repair.rollback import RollbackManager
from codegraph.repair.iteration import IterationController
from codegraph.repair.stopping import FingerprintManager, StoppingEvaluator
from codegraph.repair.safety import RepairSafetyValidator
from codegraph.repair.metrics import RepairEvaluationMetrics, calculate_repair_metrics
from codegraph.repair.pipeline import RepairPipeline

__all__ = [
    "FailureCategory",
    "FailureRecord",
    "FailureDiagnosis",
    "RepairPlan",
    "RepairIteration",
    "RepairRequest",
    "RepairResult",
    "RepairTrace",
    "FailureParser",
    "FailureDiagnoser",
    "FakeFailureDiagnoser",
    "LLMFailureDiagnoser",
    "EvidenceExpander",
    "DeterministicRepairPlanner",
    "LLMRepairPlanner",
    "RepairPlanValidator",
    "RepairPatchGenerator",
    "RollbackManager",
    "IterationController",
    "FingerprintManager",
    "StoppingEvaluator",
    "RepairSafetyValidator",
    "RepairEvaluationMetrics",
    "calculate_repair_metrics",
    "RepairPipeline",
]

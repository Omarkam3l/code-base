"""Pydantic request and response schemas for CodeGraph REST API."""

from pydantic import BaseModel, Field


class RepositoryRegisterRequest(BaseModel):
    path: str = Field(..., description="Local filesystem path to repository")
    name: str | None = Field(None, description="Optional custom repository name")
    remote_url: str | None = Field(None, description="Optional git remote URL")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Developer question or code query")
    repository_id: str = Field("repository:sample_project", description="Target repository ID")


class InvestigateRequest(BaseModel):
    question: str = Field(..., description="Investigation target question")
    repository_id: str = Field("repository:sample_project", description="Target repository ID")


class ImpactRequest(BaseModel):
    symbol: str = Field(..., description="Target symbol for impact analysis")
    repository_id: str = Field("repository:sample_project", description="Target repository ID")


class ChangePlanRequest(BaseModel):
    change_request: str = Field(..., description="Natural language change request")
    repository_id: str = Field("repository:sample_project", description="Target repository ID")


class ChangePatchRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID returned by /changes/plan (must be approved first)")
    run_tests: bool = Field(True, description="Whether to execute unit tests inside workspace during patch generation")


class ChangeCommitRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID returned by /changes/plan (must be approved first)")
    request_push: bool = Field(False, description="Whether to request remote git push (requires explicit PushController authorization)")


class EvaluationSummary(BaseModel):
    benchmark_cases: int
    status: str
    quality_gate: bool
    metrics: dict[str, str] = Field(default_factory=dict)


class RepairRequestModel(BaseModel):
    failure_message: str = Field(..., description="Test or CI failure error message")
    repository_id: str = Field("repository:sample_project", description="Target repository ID")


class APIResponse(BaseModel):
    status: str = "success"
    trace_id: str | None = None
    data: dict | list | str | None = None
    error: str | None = None

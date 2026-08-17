"""FastAPI REST API application for CodeGraph Developer Platform."""

import json
import os
import re
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from codegraph.api.models import (
    APIResponse,
    ChangeCommitRequest,
    ChangePatchRequest,
    ChangePlanRequest,
    ImpactRequest,
    InvestigateRequest,
    QueryRequest,
    RepairRequestModel,
    RepositoryRegisterRequest,
)
from codegraph.change.safety import SafetyValidator
from codegraph.observability.correlation import CorrelationContext
from codegraph.observability.redaction import SecretRedactor
from codegraph.platform.services.platform_service import PlatformService

app = FastAPI(
    title="CodeGraph Developer Platform API",
    version="16.0.0",
    description="REST API and Studio Web UI for CodeGraph RAG Code Intelligence System",
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def _build_platform_service() -> PlatformService:
    """Construct PlatformService, wiring a live Neo4j graph when credentials exist."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if uri and username and password:
        from neo4j import GraphDatabase

        from codegraph.graph.repository import GraphRepository

        driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_lifetime=300,  # don't reuse connections Aura may have dropped
        )
        graph_repo = GraphRepository(
            driver=driver, database=os.getenv("NEO4J_DATABASE")
        )
        return PlatformService(graph_repo=graph_repo)
    return PlatformService()


service = _build_platform_service()

# Optional allowlist of directories repositories may be registered from, e.g.
# "/home/deploy/repos:/data/workspaces". When unset, only the sensitive-system-path
# blocklist in SafetyValidator applies — set this in production deployments to
# restrict registration to a known set of directories.
_allowed_roots_env = os.environ.get("CODEGRAPH_ALLOWED_REPO_ROOTS", "")
ALLOWED_REPOSITORY_ROOTS = [r for r in _allowed_roots_env.split(os.pathsep) if r] or None


@app.get("/")
def get_studio_ui():
    """Serve CodeGraph Studio Web UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": "CodeGraph Studio API"})


@app.middleware("http")
async def add_correlation_headers(request: Request, call_next):
    """Middleware attaching request_id and trace_id headers to all API responses."""
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    ctx = CorrelationContext.create()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = ctx.trace_id
    return response


@app.get("/health", response_model=APIResponse)
def health_check():
    """Health check endpoint."""
    return APIResponse(status="success", data={"status": "healthy", "service": "codegraph-platform"})


@app.post("/repositories", response_model=APIResponse)
def register_repository(req: RepositoryRegisterRequest):
    """Register a new repository."""
    valid, error = SafetyValidator.validate_repository_root(req.path, allowed_roots=ALLOWED_REPOSITORY_ROOTS)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid repository path: {error}")
    res = service.register_repository(path=req.path, name=req.name)
    return APIResponse(status="success", data=res)


@app.get("/repositories", response_model=APIResponse)
def list_repositories():
    """List registered repositories."""
    repos = service.list_repositories()
    return APIResponse(status="success", data=repos)


@app.get("/repositories/{repo_id}", response_model=APIResponse)
def get_repository(repo_id: str):
    """Get repository details by ID."""
    repo = service.repo_manager.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository not found: {repo_id}")
    return APIResponse(status="success", data={"repository_id": repo.repository_id, "name": repo.name, "path": repo.path, "status": repo.status.value})


@app.post("/repositories/{repo_id}/index", response_model=APIResponse)
def refresh_repository_index(repo_id: str):
    """Trigger incremental re-indexing on repository."""
    try:
        record, summary = service.repo_manager.refresh_repository(repo_id)
        return APIResponse(status="success", data=summary)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Repository not registered: {repo_id}")


@app.post("/query", response_model=APIResponse)
def query_codebase(req: QueryRequest):
    """Execute hybrid search code query."""
    res = service.query(question=req.query, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/investigate", response_model=APIResponse)
def investigate_question(req: InvestigateRequest):
    """Execute autonomous investigation."""
    res = service.investigate(question=req.question, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/impact", response_model=APIResponse)
def analyze_impact(req: ImpactRequest):
    """Analyze symbol change impact."""
    res = service.analyze_impact(symbol=req.symbol, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/dependencies", response_model=APIResponse)
def analyze_dependencies(req: QueryRequest):
    """Analyze symbol dependencies."""
    res = service.analyze_dependencies(symbol=req.query, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/trace", response_model=APIResponse)
def trace_execution_flow(req: QueryRequest):
    """Trace call execution flow."""
    res = service.trace_execution_flow(symbol=req.query, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/changes/plan", response_model=APIResponse)
def plan_change(req: ChangePlanRequest):
    """Generate code change plan."""
    try:
        res = service.plan_change(change_request=req.change_request, repository_id=req.repository_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.post("/changes/{plan_id}/approve", response_model=APIResponse)
def approve_change_plan(plan_id: str):
    """Grant human approval for a change plan (required before patch generation)."""
    try:
        res = service.approve_plan(plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return APIResponse(status="success", data=res)


@app.post("/changes/patch", response_model=APIResponse)
def generate_patch(req: ChangePatchRequest):
    """Generate and validate a unified diff patch for an approved plan."""
    try:
        res = service.generate_or_execute_patch(plan_id=req.plan_id, run_tests=req.run_tests)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {req.plan_id}")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return APIResponse(status="success", data=res)


@app.post("/changes/{plan_id}/approve-git", response_model=APIResponse)
def approve_git_commit(plan_id: str):
    """Grant human approval for git commit execution."""
    try:
        res = service.approve_git_commit(plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return APIResponse(status="success", data=res)


@app.post("/changes/commit", response_model=APIResponse)
def execute_git_commit(req: ChangeCommitRequest):
    """Execute git commit and PR creation for an approved plan."""
    try:
        res = service.execute_git_commit_and_pr(plan_id=req.plan_id, request_push=req.request_push)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {req.plan_id}")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return APIResponse(status="success", data=res)


@app.post("/repairs", response_model=APIResponse)
def repair_failure(req: RepairRequestModel):
    """Execute iterative patch repair loop."""
    res = service.repair_failure(failure_message=req.failure_message, repository_id=req.repository_id)
    return APIResponse(status="success", trace_id=res["trace_id"], data=res)


@app.get("/traces/{trace_id}", response_model=APIResponse)
def get_trace_details(trace_id: str):
    """Get observability trace details by trace_id."""
    res = service.get_trace_details(trace_id=trace_id)
    return APIResponse(status="success", trace_id=trace_id, data=res)


@app.get("/evaluations/latest", response_model=APIResponse)
def get_latest_evaluation():
    """Latest evaluation summary derived from real artifacts (report + dataset)."""
    report_path = Path("evaluation_report.md")
    dataset_path = Path("tests/evaluation/eval_dataset_full.json")

    benchmark_cases = 0
    if dataset_path.exists():
        try:
            benchmark_cases = len(json.loads(dataset_path.read_text(encoding="utf-8")))
        except Exception:
            benchmark_cases = 0

    metrics: dict[str, str] = {}
    status = "UNKNOWN"
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        status_match = re.search(r"Benchmark Status\*\*: (\w+)", report_text)
        if status_match:
            status = status_match.group(1)
        for metric, value in re.findall(
            r"\| \*\*(\w+)\*\* \| Benchmark Value \| \*\*([0-9.]+)\*\*", report_text
        ):
            metrics[metric] = value

    return APIResponse(
        status="success",
        data={
            "benchmark_cases": benchmark_cases,
            "status": status,
            "quality_gate": status == "PASSED",
            "metrics": metrics,
        },
    )


@app.post("/repositories/{repo_id}/multimodal/index", response_model=APIResponse)
def index_multimodal_assets(repo_id: str):
    """Index multimodal repository assets (Markdown, images, diagrams)."""
    try:
        res = service.index_multimodal_assets(repository_id=repo_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return APIResponse(status="success", data=res)


@app.post("/multimodal/query", response_model=APIResponse)
def query_multimodal(req: QueryRequest):
    """Execute multimodal hybrid search query."""
    res = service.query_multimodal(query_text=req.query, repository_id=req.repository_id)
    return APIResponse(status="success", data=res)


@app.post("/multimodal/consistency", response_model=APIResponse)
def analyze_consistency(req: QueryRequest):
    """Analyze documentation and diagram drift against code graph."""
    try:
        res = service.analyze_consistency(fact=req.query, repository_id=req.repository_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return APIResponse(status="success", data=res)


@app.get("/assets/{asset_id}", response_model=APIResponse)
def get_asset_metadata(asset_id: str):
    """Get multimodal asset metadata."""
    return APIResponse(status="success", data={"asset_id": asset_id, "status": "AVAILABLE"})


@app.get("/assets/{asset_id}/evidence", response_model=APIResponse)
def get_asset_evidence(asset_id: str):
    """Get evidence citations extracted from asset."""
    return APIResponse(status="success", data={"asset_id": asset_id, "evidence": [f"Evidence extracted for asset {asset_id}"]})


@app.get("/repositories/{repo_id}/graph", response_model=APIResponse)
def get_repository_graph(repo_id: str, limit: int = 40):
    """Return a bounded snapshot of the real code graph for visualization."""
    if service.graph_repo is None:
        local_ast_data = service.get_local_ast_graph(repository_id=repo_id, limit=limit)
        return APIResponse(status="success", data=local_ast_data)
    snapshot = service.graph_repo.get_graph_snapshot(
        node_limit=max(1, min(limit, 200)), repository_id=repo_id
    )
    snapshot["repository_id"] = repo_id
    return APIResponse(status="success", data=snapshot)


@app.get("/repositories/{repo_id}/drift", response_model=APIResponse)
def get_repository_drift(repo_id: str):
    """Get all documentation drift records for repository."""
    try:
        res = service.get_repository_drift(repository_id=repo_id)
        return APIResponse(status="success", data=res)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Repository not found: {repo_id}")

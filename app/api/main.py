from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config_schema import DriftGuardConfig
from app.agents.delta_scanner import GitDeltaScanner
from app.agents.stack_detector import StackDetector
from app.agents.coordinator import CoordinatorAgent

app = FastAPI(title="DriftGuard AIDevOps API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repository: str
    branch: Optional[str] = None
    max_candidates: int = 5
    model: Optional[str] = None


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "driftguard-api",
        "version": "1.0.0",
        "root_workspace": str(PROJECT_ROOT),
    }


@app.get("/api/config")
def get_config():
    """Returns the loaded .driftguard.yml configuration."""
    cfg = DriftGuardConfig.load()
    return cfg.model_dump()


@app.get("/api/delta")
def get_delta(
    workspace: Optional[str] = Query(None, description="Workspace path"),
    base: Optional[str] = Query(None, description="Base branch or commit reference"),
    branch: Optional[str] = Query(None, description="Target branch"),
):
    """Scans and returns the incremental git delta."""
    ws = Path(workspace) if workspace else PROJECT_ROOT
    scanner = GitDeltaScanner(workspace_path=ws)
    report = scanner.scan_delta(base_branch=base, target_branch=branch)
    return report.to_dict()


@app.get("/api/stack")
def get_stack(workspace: Optional[str] = Query(None, description="Workspace path")):
    """Autonomously detects languages, frameworks, and inferred build/test commands."""
    ws = Path(workspace) if workspace else PROJECT_ROOT
    detector = StackDetector(workspace_path=ws)
    report = detector.detect_stack()
    return report.to_dict()


@app.get("/api/perception")
def get_perception(
    workspace: Optional[str] = Query(None, description="Workspace path"),
    base: Optional[str] = Query(None, description="Base reference"),
    branch: Optional[str] = Query(None, description="Target branch"),
):
    """Returns the complete Phase 1 perception report from the Coordinator Agent."""
    ws = Path(workspace) if workspace else PROJECT_ROOT
    coord = CoordinatorAgent(workspace_path=ws)
    state = coord.run_initial_perception(base_branch=base, target_branch=branch)
    return state.to_dict()


@app.get("/api/repositories")
def list_repositories():
    """Lists available workspaces. In live mode, returns current project workspace."""
    return {"repositories": [PROJECT_ROOT.name]}


@app.post("/api/analyze")
def analyze_repository(request: AnalyzeRequest):
    repo_name = request.repository

    # 1. Resolve target workspace directory
    if not repo_name or repo_name in (".", PROJECT_ROOT.name):
        target_dir = PROJECT_ROOT
    else:
        direct_path = Path(repo_name)
        if direct_path.exists() and direct_path.is_dir():
            target_dir = direct_path.resolve()
        elif (PROJECT_ROOT / repo_name).exists() and (PROJECT_ROOT / repo_name).is_dir():
            target_dir = (PROJECT_ROOT / repo_name).resolve()
        else:
            target_dir = PROJECT_ROOT

    from app.ingestion.repository_ingestor import IngestedRepository
    from app.ingestion.repository_scanner import RepositoryScanner
    from app.analysis.llm_client import LLMClient
    from app.analysis.drift_pipeline import DriftPipeline
    from app import config

    ingested = IngestedRepository(
        source_type="local",
        workspace_path=target_dir,
        original_source=repo_name or PROJECT_ROOT.name,
        commit_sha=""
    )
    scanner = RepositoryScanner()
    scanned_info = scanner.scan(ingested)

    llm = LLMClient(model=request.model or config.DEFAULT_MODEL)
    pipeline = DriftPipeline(workspace_path=target_dir, llm_client=llm)

    result = pipeline.analyze_repository(
        repo_info=scanned_info,
        max_candidates=request.max_candidates
    )

    confirmed_drifts = [r.to_dict() for r in result.get("confirmed_drifts", [])]

    return {
        "status": result.get("status"),
        "metrics": result.get("metrics"),
        "drifts": confirmed_drifts
    }


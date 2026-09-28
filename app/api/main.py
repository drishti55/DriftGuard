from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.repository_loader import RepositoryLoader

app = FastAPI(title="DriftGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, we allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    repository: str
    max_candidates: int = 5
    model: str | None = None

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/repositories")
def list_repositories():
    loader = RepositoryLoader()
    repos = loader.list_available_repos()
    return {"repositories": repos}

@app.post("/api/analyze")
def analyze_repository(request: AnalyzeRequest):
    loader = RepositoryLoader()
    repo_name = request.repository
    info = loader.get_repo_info(repo_name)

    repo_dir_name = repo_name.replace("/", "_")
    
    # We need config for REPOS_DIR
    from app import config
    target_dir = (info.snapshot_path if info and info.snapshot_path else None) or (config.REPOS_DIR / repo_dir_name)

    if not target_dir.exists():
        return {"error": "Repository not found locally."}

    from app.ingestion.repository_ingestor import IngestedRepository
    from app.ingestion.repository_scanner import RepositoryScanner
    from app.analysis.llm_client import LLMClient
    from app.analysis.drift_pipeline import DriftPipeline

    ingested = IngestedRepository(
        source_type="local",
        workspace_path=target_dir,
        original_source=repo_name,
        commit_sha=info.commit_sha if info else ""
    )
    scanner = RepositoryScanner()
    scanned_info = scanner.scan(ingested)

    llm = LLMClient(model=request.model or config.OLLAMA_MODEL)
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


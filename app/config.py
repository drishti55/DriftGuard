"""
DriftGuard Configuration
Central configuration for all paths, model settings, and thresholds.
Reads from environment variables with sensible defaults pointing to the local dataset.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Dataset Paths (local driftguard-dataset)
# ---------------------------------------------------------------------------
DATASET_DIR = PROJECT_ROOT / os.getenv("DATASET_DIR", "driftguard-dataset")
REPOS_DIR = PROJECT_ROOT / os.getenv("REPOS_DIR", "driftguard-dataset/repositories")
SNAPSHOTS_DIR = PROJECT_ROOT / os.getenv("SNAPSHOTS_DIR", "driftguard-dataset/snapshots")
METADATA_DIR = PROJECT_ROOT / os.getenv("METADATA_DIR", "driftguard-dataset/metadata")
SPLITS_DIR = PROJECT_ROOT / os.getenv("SPLITS_DIR", "driftguard-dataset/splits")
MUTATIONS_DIR = PROJECT_ROOT / os.getenv("MUTATIONS_DIR", "driftguard-dataset/mutations")

# Key metadata files
ARTIFACTS_JSON = METADATA_DIR / "artifacts.json"
CASES_JSONL = METADATA_DIR / "cases.jsonl"
CLONE_RESULTS_JSON = METADATA_DIR / "clone_results.json"
NATURAL_DRIFTS_JSON = METADATA_DIR / "natural_drifts.json"
MUTATIONS_JSON = METADATA_DIR / "mutations.json"
REPOSITORIES_JSON = METADATA_DIR / "repositories.json"
COMMITS_JSON = METADATA_DIR / "commits.json"

# Split files
TRAIN_JSONL = SPLITS_DIR / "train.jsonl"
VALIDATION_JSONL = SPLITS_DIR / "validation.jsonl"
TEST_JSONL = SPLITS_DIR / "test.jsonl"

# ---------------------------------------------------------------------------
# Ollama / LLM Settings
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "codellama:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

SUPPORTED_MODELS = [
    "qwen2.5-coder:7b",
    "starcoder2:3b",
    "deepseek-coder-v2:16b",
    "codestral:22b",
    "codellama:7b",
    "gemma2:9b"
]

# ---------------------------------------------------------------------------
# Embedding / RAG Settings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", ".chroma_db")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))

# ---------------------------------------------------------------------------
# Evaluation Settings
# ---------------------------------------------------------------------------
EVAL_SAMPLE_SIZE = int(os.getenv("EVAL_SAMPLE_SIZE", "200"))
EVAL_RANDOM_SEED = int(os.getenv("EVAL_RANDOM_SEED", "42"))

# Results directories
RESULTS_DIR = PROJECT_ROOT / "results"
PREDICTIONS_DIR = RESULTS_DIR / "predictions"
METRICS_DIR = RESULTS_DIR / "metrics"
REPORTS_DIR = RESULTS_DIR / "reports"

# ---------------------------------------------------------------------------
# Drift Categories
# ---------------------------------------------------------------------------
DRIFT_TYPES = [
    "documentation_vs_code",
    "test_vs_code",
    "api_spec_vs_code",
    "dependency_vs_code",
    "ci_vs_project",
    "docker_vs_project",
    "build_config_vs_project",
    "configuration_vs_code",
    "no_drift",
]

SEVERITY_LEVELS = ["none", "low", "medium", "high"]

# ---------------------------------------------------------------------------
# File size limits
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_BYTES = 100_000  # Skip files larger than 100KB for LLM context
MAX_CONTEXT_CHARS = 8000       # Max chars sent to LLM per artifact

# ---------------------------------------------------------------------------
# GitHub (optional)
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def ensure_dirs():
    """Create output directories if they don't exist."""
    for d in [RESULTS_DIR, PREDICTIONS_DIR, METRICS_DIR, REPORTS_DIR, CHROMA_PERSIST_DIR]:
        d.mkdir(parents=True, exist_ok=True)

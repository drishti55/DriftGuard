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
# Model Gateway Settings (OmniRoute / Ollama)
# ---------------------------------------------------------------------------
OMNIROUTE_HOST = os.getenv("OMNIROUTE_HOST", "http://localhost:20128/v1")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")
DEFAULT_MODEL = os.getenv("DRIFTGUARD_MODEL", "auto/best-fast")

# Local Ollama fallback settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "codellama:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# Embedding / RAG Settings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", ".chroma_db")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))

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
    """Create persistent output directories if they don't exist."""
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)


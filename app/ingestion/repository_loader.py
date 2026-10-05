"""
DriftGuard Repository Loader
Loads repository data from the local driftguard-dataset.
Resolves repos, snapshots, and artifact metadata from disk.
"""

import logging
from pathlib import Path
from typing import Optional, List

from app import config
from app.ingestion.file_classifier import classify_file

logger = logging.getLogger(__name__)


from app.ingestion.models import RepoArtifact, RepoInfo

__all__ = ["RepoArtifact", "RepoInfo", "RepositoryLoader"]


class RepositoryLoader:
    """
    Lightweight workspace / repository loader for local repositories.
    Provides backward-compatible interface for loading repository artifacts from disk.
    """

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = Path(workspace_path) if workspace_path else config.PROJECT_ROOT

    def list_available_repos(self) -> List[str]:
        """List active workspace name."""
        return [self.workspace_path.name]

    def get_repo_info(self, repo_name: str) -> Optional[RepoInfo]:
        """Get repository info for local workspace or directory path."""
        p = Path(repo_name)
        target_path = p.resolve() if p.exists() and p.is_dir() else self.workspace_path
        return RepoInfo(
            full_name=target_path.name,
            local_path=target_path,
            snapshot_path=target_path,
        )

    def load_repo_artifacts(self, repo_name: str, use_metadata: bool = False) -> List[RepoArtifact]:
        """Scan the repo directory on disk and classify files."""
        return self._scan_from_disk(repo_name)

    def _scan_from_disk(self, repo_name: str) -> List[RepoArtifact]:
        """Scan the repo directory on disk and classify files."""
        info = self.get_repo_info(repo_name)
        if not info:
            return []

        scan_dir = info.snapshot_path or info.local_path
        if not scan_dir or not scan_dir.exists():
            return []

        artifacts = []
        for file_path in scan_dir.rglob("*"):
            if file_path.is_dir():
                continue

            rel_path = str(file_path.relative_to(scan_dir))
            if any(part.startswith('.') for part in rel_path.split('/')):
                if not rel_path.startswith('.github/'):
                    continue
            skip_dirs = {'node_modules', 'vendor', '__pycache__', '.git', 'venv', 'env'}
            if any(d in rel_path.split('/') for d in skip_dirs):
                continue

            artifact_type = classify_file(rel_path)
            artifacts.append(RepoArtifact(
                path=rel_path,
                artifact_type=artifact_type,
                size_bytes=file_path.stat().st_size,
                extension=file_path.suffix,
            ))

        return artifacts

    def read_file_content(self, repo_name: str, file_path: str,
                          commit_sha: str = None,
                          max_chars: int = None) -> str:
        """Read actual file content from disk with character limits."""
        max_chars = max_chars or config.MAX_CONTEXT_CHARS
        target_dir = Path(repo_name) if Path(repo_name).is_dir() else self.workspace_path
        full_path = target_dir / file_path
        if full_path.exists():
            return self._read_with_limit(full_path, max_chars)

        return "[File not found on disk]"

    def _read_with_limit(self, path: Path, max_chars: int) -> str:
        """Read file with character limit."""
        try:
            size = path.stat().st_size
            if size > config.MAX_FILE_SIZE_BYTES:
                with open(path, 'r', errors='replace') as f:
                    content = f.read(max_chars)
                return content + "\n... [truncated — file too large]"

            with open(path, 'r', errors='replace') as f:
                content = f.read()
            if len(content) > max_chars:
                content = content[:max_chars] + "\n... [truncated]"
            return content
        except Exception as e:
            return f"[Error reading file: {e}]"


"""
DriftGuard Repository Loader
Loads repository data from the local driftguard-dataset.
Resolves repos, snapshots, and artifact metadata from disk.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from app import config
from app.ingestion.file_classifier import classify_file

logger = logging.getLogger(__name__)


@dataclass
class RepoArtifact:
    """A single file/artifact from a repository."""
    path: str
    artifact_type: str
    size_bytes: int = 0
    extension: str = ""
    # Complete inventory fields
    artifact_id: str = ""
    file_type: str = ""
    language: str = ""
    artifact_category: str = ""
    file_size: int = 0
    line_count: int = 0
    parse_status: str = "Parsed"
    parser: str = "ast_regex_parser"
    content_hash: str = ""
    status: str = "RELEVANT"  # "RELEVANT" or "IGNORED"
    ignore_reason: Optional[str] = None
    extracted_info: Optional[object] = None
    relationships_count: int = 0
    drifts_count: int = 0
    # Backwards-compatibility metadata fields
    imports: List[dict] = field(default_factory=list)
    function_signatures: List[dict] = field(default_factory=list)
    api_routes: List[dict] = field(default_factory=list)
    content_snippet: str = ""
    parsed_dependencies: List[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.artifact_id:
            self.artifact_id = self.path
        if not self.artifact_category:
            self.artifact_category = self.artifact_type
        if not self.file_size and self.size_bytes:
            self.file_size = self.size_bytes


@dataclass
class RepoInfo:
    """Repository information, its complete inventory, and relationship graph."""
    full_name: str
    local_path: Optional[Path] = None
    snapshot_path: Optional[Path] = None
    commit_sha: str = ""
    language: str = ""
    framework: str = ""
    package_manager: str = ""
    artifacts: List[RepoArtifact] = field(default_factory=list)
    artifact_type_counts: Dict[str, int] = field(default_factory=dict)
    scan_metrics: Dict[str, int] = field(default_factory=dict)
    drift_candidates: List[dict] = field(default_factory=list)


class RepositoryLoader:
    """
    Loads repository data from the local driftguard-dataset.
    Uses pre-extracted artifact metadata from artifacts.json when available,
    falls back to scanning the repo directory on disk.
    """

    def __init__(self):
        self._clone_data = None
        self._artifacts_index = None  # repo_name -> list of artifact dicts

    def _load_clone_data(self) -> dict:
        """Load clone_results.json for repo path resolution."""
        if self._clone_data is None:
            self._clone_data = {}
            if config.CLONE_RESULTS_JSON.exists():
                with open(config.CLONE_RESULTS_JSON) as f:
                    data = json.load(f)
                for r in data.get("results", []):
                    self._clone_data[r["full_name"]] = r
        return self._clone_data

    def _load_artifacts_index(self) -> dict:
        """
        Load artifacts.json and index by repository name.
        This is a large file (~695MB) so we load it once and cache.
        """
        if self._artifacts_index is not None:
            return self._artifacts_index

        self._artifacts_index = {}
        if config.ARTIFACTS_JSON.exists():
            logger.info("Loading artifacts index (this may take a moment)...")
            with open(config.ARTIFACTS_JSON) as f:
                data = json.load(f)
            for artifact in data.get("artifacts", []):
                repo = artifact.get("repository", "")
                if repo not in self._artifacts_index:
                    self._artifacts_index[repo] = []
                self._artifacts_index[repo].append(artifact)
            logger.info(f"Loaded artifacts for {len(self._artifacts_index)} repositories")
        return self._artifacts_index

    def list_available_repos(self) -> List[str]:
        """List all repository names available locally."""
        clone_data = self._load_clone_data()
        return sorted(clone_data.keys())

    def get_repo_info(self, repo_name: str) -> Optional[RepoInfo]:
        """
        Get repository information by full name (e.g., 'tiangolo/fastapi').

        Args:
            repo_name: GitHub-style 'owner/repo' name

        Returns:
            RepoInfo with local paths and artifacts, or None if not found
        """
        clone_data = self._load_clone_data()

        if repo_name not in clone_data:
            logger.warning(f"Repository {repo_name} not found in clone results")
            return None

        repo_data = clone_data[repo_name]
        repo_dir_name = repo_name.replace("/", "_")

        # Resolve local path
        local_path = config.REPOS_DIR / repo_dir_name
        if not local_path.exists():
            local_path = None

        # Resolve snapshot path (use first available)
        snapshot_path = None
        commit_sha = ""
        for snapshot in repo_data.get("snapshots", []):
            sp = Path(snapshot["path"])
            if sp.exists():
                snapshot_path = sp
                commit_sha = snapshot.get("commit_sha", "")
                break

        info = RepoInfo(
            full_name=repo_name,
            local_path=local_path,
            snapshot_path=snapshot_path,
            commit_sha=commit_sha,
            language=repo_data.get("language", ""),
        )

        return info

    def load_repo_artifacts(self, repo_name: str,
                            use_metadata: bool = True) -> List[RepoArtifact]:
        """
        Load all artifacts for a repository.

        If use_metadata=True, reads from the pre-extracted artifacts.json (fast).
        Otherwise, scans the repo directory on disk (slower but works for new repos).

        Args:
            repo_name: GitHub-style 'owner/repo' name
            use_metadata: Whether to use pre-extracted metadata

        Returns:
            List of RepoArtifact objects
        """
        if use_metadata:
            return self._load_from_metadata(repo_name)
        else:
            return self._scan_from_disk(repo_name)

    def _load_from_metadata(self, repo_name: str) -> List[RepoArtifact]:
        """Load artifacts from pre-extracted artifacts.json."""
        index = self._load_artifacts_index()

        if repo_name not in index:
            logger.warning(f"No artifacts metadata for {repo_name}")
            return []

        artifacts = []
        for raw in index[repo_name]:
            artifact = RepoArtifact(
                path=raw.get("path", ""),
                artifact_type=raw.get("type", "other"),
                size_bytes=raw.get("size_bytes", 0),
                extension=raw.get("extension", ""),
                imports=raw.get("imports", []),
                function_signatures=raw.get("function_signatures", []),
                api_routes=raw.get("api_routes", []),
                content_snippet=raw.get("content_snippet", ""),
                parsed_dependencies=raw.get("parsed_dependencies", []),
            )
            artifacts.append(artifact)

        return artifacts

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

            # Skip hidden dirs, node_modules, vendor, etc.
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
        """
        Read actual file content from disk.

        Args:
            repo_name: 'owner/repo'
            file_path: Relative path within the repo
            commit_sha: Optional commit SHA for snapshot lookup
            max_chars: Max characters to return

        Returns:
            File content as string
        """
        max_chars = max_chars or config.MAX_CONTEXT_CHARS
        repo_dir_name = repo_name.replace("/", "_")

        # Try snapshot first
        if commit_sha:
            snapshot_name = f"{repo_dir_name}_{commit_sha[:8]}"
            full_path = config.SNAPSHOTS_DIR / snapshot_name / file_path
            if full_path.exists():
                return self._read_with_limit(full_path, max_chars)

        # Try repo directory
        full_path = config.REPOS_DIR / repo_dir_name / file_path
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

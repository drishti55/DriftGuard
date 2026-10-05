"""
DriftGuard Ingestion Models
Canonical data structures representing repository artifacts, inventories, and scan metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


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

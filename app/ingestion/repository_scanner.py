"""
DriftGuard Repository Scanner
Recursively scans an ingested repository workspace to discover its complete structure,
builds an accurate inventory, excludes vendor/binary/cache assets explicitly,
detects the true language, and generates fact-based relationship candidates.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Tuple
from collections import Counter
import logging

from app.ingestion.repository_ingestor import IngestedRepository
from app.ingestion.repository_loader import RepoInfo, RepoArtifact
from app.ingestion.file_classifier import (
    classify_file, is_ignored_path, get_file_type_description,
    IGNORED_BINARY_EXTENSIONS
)
from app.ingestion.artifact_extractor import extract_info
from app.analysis.relationship_graph import RelationshipGraph

logger = logging.getLogger(__name__)


class RepositoryScanner:
    """Scans an ingested repository to determine its properties, inventory, and relationships."""

    LANGUAGE_EXTENSIONS = {
        '.py': 'Python',
        '.go': 'Go',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React JSX',
        '.tsx': 'React TSX',
        '.java': 'Java',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.cs': 'C#',
        '.cpp': 'C++',
        '.c': 'C',
        '.sh': 'Shell',
        '.bash': 'Bash',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
    }

    def __init__(self):
        pass

    def scan(self, ingested_repo: IngestedRepository) -> RepoInfo:
        """
        Scan the ingested repository workspace.
        Builds complete inventory of both relevant and ignored artifacts.
        """
        workspace = Path(ingested_repo.workspace_path).resolve()
        artifacts: List[RepoArtifact] = []

        total_files = 0
        ignored_vendor_cache = 0
        ignored_binary = 0
        relevant_source_lang_counts = Counter()

        for root, dirs, files in os.walk(workspace):
            rel_root = Path(root).relative_to(workspace)
            rel_root_str = str(rel_root).replace("\\", "/")

            # Check if this entire directory is an ignored vendor/theme/cache directory
            dir_ignored, dir_reason = is_ignored_path(rel_root_str + "/dummy")
            if dir_ignored:
                sub_count = sum(len(f_list) for _, _, f_list in os.walk(root))
                total_files += sub_count
                ignored_vendor_cache += sub_count
                
                artifacts.append(RepoArtifact(
                    path=rel_root_str,
                    artifact_type="ignored",
                    artifact_category="ignored",
                    size_bytes=0,
                    extension="",
                    file_type=f"Vendor/Theme Subtree ({sub_count} files)",
                    status="IGNORED",
                    ignore_reason=dir_reason,
                    parse_status="Skipped",
                    parser="none",
                ))
                # Prune walking deeper into this ignored directory
                dirs.clear()
                continue

            for file in files:
                total_files += 1
                file_path = Path(root) / file
                rel_file = str((rel_root / file) if str(rel_root) != "." else Path(file)).replace("\\", "/")
                ext = file_path.suffix.lower()

                # Check explicit ignore condition for individual file
                is_ignored, ignore_reason = is_ignored_path(rel_file)

                # Skip hidden dotfiles unless they are explicit config files
                if file.startswith('.') and file not in {
                    '.env', '.env.example', '.gitignore', '.dockerignore', 
                    '.gitlab-ci.yml', '.golangci.yml', '.yamllint.yml', 
                    '.prettierrc', '.eslintrc', '.editorconfig'
                } and not rel_file.startswith('.github/'):
                    is_ignored = True
                    ignore_reason = "Hidden configuration file"

                file_size = file_path.stat().st_size if file_path.exists() else 0

                if is_ignored:
                    if ext in IGNORED_BINARY_EXTENSIONS:
                        ignored_binary += 1
                    else:
                        ignored_vendor_cache += 1

                    artifacts.append(RepoArtifact(
                        path=rel_file,
                        artifact_type="ignored",
                        artifact_category="ignored",
                        size_bytes=file_size,
                        extension=ext,
                        file_type=get_file_type_description(rel_file, "ignored"),
                        status="IGNORED",
                        ignore_reason=ignore_reason,
                        parse_status="Skipped",
                        parser="none",
                    ))
                    continue

                # RELEVANT ARTIFACT: Classify and extract facts
                category = classify_file(rel_file)
                file_type_desc = get_file_type_description(rel_file, category)

                # Track language for relevant source code / tests
                lang = self.LANGUAGE_EXTENSIONS.get(ext, "")
                if category in ("source_code", "test") and lang:
                    relevant_source_lang_counts[lang] += 1

                # Read line count and content hash for relevant artifacts
                line_count = 0
                content_hash = ""
                extracted_facts = None
                parse_status = "Unparsed"

                try:
                    if file_size < 1_000_000:  # Under 1MB
                        content = file_path.read_text(errors='replace')
                        line_count = content.count('\n') + 1
                        content_hash = hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()[:12]
                        extracted_facts = extract_info(content, rel_file)
                        parse_status = "Parsed"
                except Exception as e:
                    parse_status = f"Error: {e}"

                artifact = RepoArtifact(
                    path=rel_file,
                    artifact_type=category,
                    artifact_category=category,
                    size_bytes=file_size,
                    extension=ext,
                    file_type=file_type_desc,
                    language=lang,
                    line_count=line_count,
                    content_hash=content_hash,
                    status="RELEVANT",
                    ignore_reason=None,
                    extracted_info=extracted_facts,
                    parse_status=parse_status,
                    parser="ast_regex_parser" if parse_status == "Parsed" else "none",
                )
                artifacts.append(artifact)

        # Detect primary language strictly from RELEVANT source files
        primary_lang = "Unknown"
        if relevant_source_lang_counts:
            primary_lang = relevant_source_lang_counts.most_common(1)[0][0]

        # Detect framework & package manager
        framework, package_manager = self._detect_framework_and_pm(workspace)

        # Count relevant categories
        relevant_artifacts = [a for a in artifacts if a.status == "RELEVANT"]
        artifact_type_counts = dict(Counter(a.artifact_category for a in relevant_artifacts))

        # Build repository relationship graph & generate candidates
        graph = RelationshipGraph(workspace_path=workspace)
        edges = graph.build_graph(relevant_artifacts)
        candidates = graph.generate_candidates()

        scan_metrics = {
            "files_discovered": total_files,
            "relevant_artifacts": len(relevant_artifacts),
            "ignored_vendor_cache": ignored_vendor_cache,
            "ignored_binary": ignored_binary,
            "relationships_discovered": len(edges),
            "candidates_generated": len(candidates),
        }

        logger.info(f"Scan complete: {scan_metrics}")

        return RepoInfo(
            full_name=ingested_repo.original_source,
            local_path=workspace,
            snapshot_path=None,
            commit_sha=ingested_repo.commit_sha or "",
            language=primary_lang,
            framework=framework,
            package_manager=package_manager,
            artifacts=artifacts,
            artifact_type_counts=artifact_type_counts,
            scan_metrics=scan_metrics,
            drift_candidates=candidates,
        )

    def _detect_framework_and_pm(self, workspace: Path) -> Tuple[str, str]:
        """Attempt to detect framework and package manager from workspace files."""
        framework = "Unknown"
        package_manager = "Unknown"

        # Go
        if (workspace / "go.mod").exists():
            package_manager = "go modules"
            try:
                mod_content = (workspace / "go.mod").read_text(errors='ignore')
                if "sigs.k8s.io/controller-runtime" in mod_content or "k8s.io/client-go" in mod_content:
                    framework = "Kubernetes Operator SDK"
                elif "gin-gonic/gin" in mod_content:
                    framework = "Gin"
                elif "labstack/echo" in mod_content:
                    framework = "Echo"
                elif "gofiber/fiber" in mod_content:
                    framework = "Fiber"
                else:
                    framework = "Standard Go"
            except Exception:
                framework = "Go"

        # Python
        elif (workspace / "requirements.txt").exists():
            package_manager = "pip"
            reqs = (workspace / "requirements.txt").read_text(errors='ignore').lower()
            if "fastapi" in reqs: framework = "FastAPI"
            elif "flask" in reqs: framework = "Flask"
            elif "django" in reqs: framework = "Django"
            
        elif (workspace / "pyproject.toml").exists():
            package_manager = "poetry/pipenv"
            pyproj = (workspace / "pyproject.toml").read_text(errors='ignore').lower()
            if "fastapi" in pyproj: framework = "FastAPI"
            elif "flask" in pyproj: framework = "Flask"
            elif "django" in pyproj: framework = "Django"

        # Node.js
        elif (workspace / "package.json").exists():
            try:
                with open(workspace / "package.json", 'r', errors='ignore') as f:
                    pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                package_manager = "npm"
                if (workspace / "yarn.lock").exists(): package_manager = "yarn"
                elif (workspace / "pnpm-lock.yaml").exists(): package_manager = "pnpm"
                
                if "next" in deps: framework = "Next.js"
                elif "react" in deps: framework = "React"
                elif "vue" in deps: framework = "Vue"
                elif "express" in deps: framework = "Express"
                elif "nestjs" in deps or "@nestjs/core" in deps: framework = "NestJS"
            except Exception:
                pass

        # Rust
        elif (workspace / "Cargo.toml").exists():
            package_manager = "cargo"
            framework = "Rust"

        return framework, package_manager

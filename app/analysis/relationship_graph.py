"""
DriftGuard Repository Relationship Graph
Builds deterministic cross-artifact relationships from repository evidence:
imports, tests, API routes, configurations, documentation mentions, and deployment specs.
Generates genuine drift candidates without arbitrary cartesian explosion or truncation.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from app.ingestion.repository_loader import RepoArtifact
from app.ingestion.artifact_extractor import extract_info, ExtractedInfo

logger = logging.getLogger(__name__)


@dataclass
class RelationshipEdge:
    """A verified relationship between two artifacts in the repository."""
    artifact_1_path: str
    artifact_1_type: str
    artifact_2_path: str
    artifact_2_type: str
    relationship_type: str
    rationale: str
    evidence_context: Dict[str, any] = field(default_factory=dict)


class RelationshipGraph:
    """
    Constructs an evidence-grounded dependency & relationship graph across
    all relevant artifacts in a repository workspace.
    """

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.edges: List[RelationshipEdge] = []
        self._artifacts_by_path: Dict[str, RepoArtifact] = {}
        self._artifacts_by_category: Dict[str, List[RepoArtifact]] = defaultdict(list)

    def build_graph(self, artifacts: List[RepoArtifact]) -> List[RelationshipEdge]:
        """
        Build the relationship graph across all relevant repository artifacts.
        """
        self.edges = []
        self._artifacts_by_path = {a.path: a for a in artifacts if a.status == "RELEVANT"}
        self._artifacts_by_category = defaultdict(list)
        for a in self._artifacts_by_path.values():
            self._artifacts_by_category[a.artifact_category].append(a)

        # Ensure extracted_info is populated for all relevant artifacts
        self._ensure_facts_extracted()

        seen_pairs: Set[Tuple[str, str]] = set()

        def add_edge(a1: RepoArtifact, a2: RepoArtifact, rel_type: str, rationale: str, ctx: dict = None):
            pair_key = (min(a1.path, a2.path), max(a1.path, a2.path))
            if pair_key in seen_pairs or a1.path == a2.path:
                return
            seen_pairs.add(pair_key)
            edge = RelationshipEdge(
                artifact_1_path=a1.path,
                artifact_1_type=a1.artifact_category,
                artifact_2_path=a2.path,
                artifact_2_type=a2.artifact_category,
                relationship_type=rel_type,
                rationale=rationale,
                evidence_context=ctx or {}
            )
            self.edges.append(edge)
            a1.relationships_count += 1
            a2.relationships_count += 1

        # 1. TEST <-> IMPLEMENTATION RELATIONSHIPS
        self._build_test_relationships(add_edge)

        # 2. DEPENDENCY <-> CODE RELATIONSHIPS
        self._build_dependency_relationships(add_edge)

        # 3. API SPECIFICATION <-> IMPLEMENTATION RELATIONSHIPS
        self._build_api_spec_relationships(add_edge)

        # 4. DOCUMENTATION <-> CODE & CONFIG RELATIONSHIPS
        self._build_doc_relationships(add_edge)

        # 5. CONFIGURATION <-> CODE RELATIONSHIPS
        self._build_config_relationships(add_edge)

        # 6. DOCKER / DEPLOYMENT <-> CODE & DEPENDENCY RELATIONSHIPS
        self._build_docker_deployment_relationships(add_edge)

        # 7. CI/CD <-> PROJECT & BUILD RELATIONSHIPS
        self._build_ci_relationships(add_edge)

        logger.info(f"Built relationship graph with {len(self.edges)} edges across {len(self._artifacts_by_path)} artifacts.")
        return self.edges

    def _ensure_facts_extracted(self):
        """Extract structured facts for each artifact if content is accessible."""
        for a in self._artifacts_by_path.values():
            if a.extracted_info is None and self.workspace_path:
                file_path = self.workspace_path / a.path
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text(errors='replace')
                        a.line_count = content.count('\n') + 1
                        a.extracted_info = extract_info(content, a.path)
                        a.parse_status = "Parsed"
                    except Exception as e:
                        logger.warning(f"Error parsing {a.path}: {e}")
                        a.parse_status = f"Error: {e}"

    def _build_test_relationships(self, add_edge):
        """Match tests to their corresponding implementation files deterministically."""
        tests = self._artifacts_by_category.get("test", [])
        sources = self._artifacts_by_category.get("source_code", [])
        source_paths = {s.path: s for s in sources}
        source_by_stem = {Path(s.path).stem.lower(): s for s in sources}

        for t in tests:
            t_path = Path(t.path)
            t_stem = t_path.stem.lower()

            # Skip __init__ files: every package has one, they match everything and
            # create meaningless cross-package edges.
            if t_stem == '__init__':
                continue

            # Direct file name match (e.g. redis_test.go -> redis.go, test_user.py -> user.py)
            clean_stems = [
                t_stem.replace("_test", ""),
                t_stem.replace(".test", ""),
                t_stem.replace(".spec", ""),
                t_stem.replace("test_", ""),
                t_stem.replace("test", "")
            ]

            # Drop any empty or trivially short stems that would match too broadly.
            matched = False
            for cand_stem in clean_stems:
                if cand_stem and len(cand_stem) >= 2 and cand_stem != '__init__' and cand_stem in source_by_stem:
                    s_art = source_by_stem[cand_stem]
                    add_edge(t, s_art, "test_vs_code", f"Unit test matches implementation by name: {t_path.name} ↔ {Path(s_art.path).name}")
                    matched = True
                    break

            # Sibling directory match — only when test and source share a *non-root* parent dir.
            if not matched:
                parent_dir = str(t_path.parent)
                # Skip root-level siblings — every file in root would pair with every test.
                if parent_dir not in ('.', ''):
                    for s in sources:
                        if str(Path(s.path).parent) == parent_dir and s.path != t.path:
                            add_edge(t, s, "test_vs_code", f"Test resides in same subsystem directory: {parent_dir}")
                            break

    def _build_dependency_relationships(self, add_edge):
        """Match dependency manifests to source files that import packages."""
        dependencies = self._artifacts_by_category.get("dependency", [])
        sources = self._artifacts_by_category.get("source_code", [])

        for dep in dependencies:
            dep_info: Optional[ExtractedInfo] = getattr(dep, "extracted_info", None)
            dep_names = set()
            if dep_info:
                dep_names = {d.value.split()[0].lower() for d in dep_info.dependencies}

            dep_parent = str(Path(dep.path).parent)

            for s in sources:
                s_info: Optional[ExtractedInfo] = getattr(s, "extracted_info", None)
                if not s_info:
                    continue

                # Match by explicit imports
                imported_pkgs = {imp.value.split('/')[0].lower() for imp in s_info.imports}
                overlap = imported_pkgs.intersection(dep_names)
                if overlap:
                    add_edge(dep, s, "dependency_vs_code", f"Source imports declared package(s): {', '.join(list(overlap)[:3])}")
                elif dep_parent == "." or str(Path(s.path).parent).startswith(dep_parent):
                    # In same project/module root: connect root entrypoints
                    if Path(s.path).stem.lower() in ('main', 'app', 'index', 'server', 'lib'):
                        add_edge(dep, s, "dependency_vs_code", f"Root manifest applies to main module entrypoint: {s.path}")

    def _build_api_spec_relationships(self, add_edge):
        """Match OpenAPI / Swagger routes to code handlers/routes."""
        api_specs = self._artifacts_by_category.get("api_specification", [])
        sources = self._artifacts_by_category.get("source_code", [])

        for spec in api_specs:
            spec_info: Optional[ExtractedInfo] = getattr(spec, "extracted_info", None)
            spec_routes = set()
            if spec_info:
                spec_routes = {r.value.lower() for r in spec_info.api_routes if r.value.startswith('/')}

            for s in sources:
                s_info: Optional[ExtractedInfo] = getattr(s, "extracted_info", None)
                if not s_info or not s_info.api_routes:
                    continue
                code_routes = {r.value.lower() for r in s_info.api_routes}
                matched_routes = [r for r in code_routes if any(sr in r for sr in spec_routes)]
                if matched_routes:
                    add_edge(spec, s, "api_spec_vs_code", f"API specification defines route implemented in code: {matched_routes[0]}")
                elif any(word in s.path.lower() for word in ('api', 'router', 'handler', 'controller')):
                    add_edge(spec, s, "api_spec_vs_code", f"API specification maps to controller: {s.path}")

    def _build_doc_relationships(self, add_edge):
        """Match documentation to source code, configs, and deployment files."""
        docs = self._artifacts_by_category.get("documentation", [])
        sources = self._artifacts_by_category.get("source_code", [])
        configs = self._artifacts_by_category.get("other_configuration", [])
        deployments = self._artifacts_by_category.get("deployment_configuration", [])

        for d in docs:
            d_info: Optional[ExtractedInfo] = getattr(d, "extracted_info", None)
            d_name = Path(d.path).name.lower()

            # Root README connects to primary entrypoints and primary deployment configuration
            if d.path.lower() in ('readme.md', 'readme.rst', 'readme'):
                for s in sources:
                    if Path(s.path).stem.lower() in ('main', 'app', 'index', 'server', 'cli', 'version'):
                        add_edge(d, s, "documentation_vs_code", f"README documents core entrypoint: {s.path}")
                for cfg in configs:
                    if '.env' in cfg.path.lower() or cfg.path.lower() in ('config.yaml', 'config.yml', 'config.json'):
                        add_edge(d, cfg, "documentation_vs_config", f"README documents project configuration: {cfg.path}")
                for dep in deployments:
                    if 'values.yaml' in dep.path.lower() or 'chart.yaml' in dep.path.lower():
                        add_edge(d, dep, "documentation_vs_deployment", f"README documents deployment configuration: {dep.path}")

            # Specific referenced paths in doc (explicit mention in text)
            if d_info and d_info.referenced_paths:
                ref_set = {r.value.lower() for r in d_info.referenced_paths}
                for a_path, a in self._artifacts_by_path.items():
                    if a_path.lower() in ref_set or Path(a_path).name.lower() in ref_set:
                        add_edge(d, a, "documentation_vs_code", f"Documentation explicitly references file: {a_path}")

    def _build_config_relationships(self, add_edge):
        """Match configs (.env.example, config.yaml) to code reading those keys."""
        configs = self._artifacts_by_category.get("other_configuration", [])
        sources = self._artifacts_by_category.get("source_code", [])

        for c in configs:
            c_info: Optional[ExtractedInfo] = getattr(c, "extracted_info", None)
            c_keys = set()
            if c_info:
                c_keys = {k.value.upper() for k in c_info.config_keys}

            for s in sources:
                s_info: Optional[ExtractedInfo] = getattr(s, "extracted_info", None)
                if not s_info:
                    continue
                code_keys = {k.value.upper() for k in s_info.config_keys}
                overlap = c_keys.intersection(code_keys)
                if overlap:
                    add_edge(c, s, "config_vs_code", f"Source code reads configuration key(s): {', '.join(list(overlap)[:3])}")

    def _build_docker_deployment_relationships(self, add_edge):
        """Match Dockerfiles and Deployment configs to code and dependencies."""
        dockers = self._artifacts_by_category.get("docker_configuration", [])
        deployments = self._artifacts_by_category.get("deployment_configuration", [])
        dependencies = self._artifacts_by_category.get("dependency", [])
        sources = self._artifacts_by_category.get("source_code", [])

        for dk in dockers:
            for dep in dependencies:
                add_edge(dk, dep, "docker_vs_project", f"Dockerfile manages build dependencies from {dep.path}")
            for s in sources:
                if Path(s.path).stem.lower() in ('main', 'app', 'index', 'server'):
                    add_edge(dk, s, "docker_vs_project", f"Dockerfile builds entrypoint binary: {s.path}")

        for deploy in deployments:
            if 'values.yaml' in deploy.path:
                for dk in dockers:
                    add_edge(deploy, dk, "deployment_vs_docker", f"Deployment values reference container specification in {dk.path}")
                for s in sources:
                    if Path(s.path).stem.lower() in ('main', 'server'):
                        add_edge(deploy, s, "deployment_vs_code", f"Deployment manifest configures service {s.path}")

    def _build_ci_relationships(self, add_edge):
        """Match CI workflows to build configs and test files."""
        ci_files = self._artifacts_by_category.get("ci_configuration", [])
        builds = self._artifacts_by_category.get("build_configuration", [])
        deps = self._artifacts_by_category.get("dependency", [])

        for ci in ci_files:
            for b in builds:
                if Path(b.path).name.lower() in ('makefile', 'package.json'):
                    add_edge(ci, b, "ci_vs_project", f"CI workflow invokes targets from {b.path}")
            for dep in deps:
                add_edge(ci, dep, "ci_vs_project", f"CI workflow installs packages declared in {dep.path}")

    def generate_candidates(self) -> List[Dict]:
        """
        Convert all relationship edges into analysis candidate cases.
        Every relevant relationship is represented as a candidate case.
        """
        candidates = []
        for i, edge in enumerate(self.edges):
            candidates.append({
                "case_id": f"rel-{i:04d}",
                "relationship_type": edge.relationship_type,
                "rationale": edge.rationale,
                "artifact_1": {
                    "path": edge.artifact_1_path,
                    "type": edge.artifact_1_type,
                },
                "artifact_2": {
                    "path": edge.artifact_2_path,
                    "type": edge.artifact_2_type,
                },
                "evidence_context": edge.evidence_context,
            })
        return candidates

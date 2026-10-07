"""
DriftGuard Stack Detector Agent
Autonomously detects repository technology stacks, frameworks, package managers,
and infers appropriate build, lint, and test validation commands.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.config_schema import DriftGuardConfig, BuildTargetConfig

logger = logging.getLogger(__name__)


@dataclass
class ComponentStack:
    """Represents a single detected tech stack component within the repository."""
    name: str
    working_directory: str
    primary_language: str
    frameworks: List[str] = field(default_factory=list)
    package_manager: str = "unknown"
    inferred_build_command: Optional[str] = None
    inferred_test_command: Optional[str] = None
    manifest_files: List[str] = field(default_factory=list)


@dataclass
class StackReport:
    """Complete summary of detected technologies across the workspace."""
    workspace_path: str
    is_polyglot: bool
    components: List[ComponentStack] = field(default_factory=list)
    detected_languages: List[str] = field(default_factory=list)
    effective_build_matrix: Dict[str, BuildTargetConfig] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "workspace_path": self.workspace_path,
            "is_polyglot": self.is_polyglot,
            "detected_languages": self.detected_languages,
            "components": [
                {
                    "name": c.name,
                    "working_directory": c.working_directory,
                    "primary_language": c.primary_language,
                    "frameworks": c.frameworks,
                    "package_manager": c.package_manager,
                    "inferred_build_command": c.inferred_build_command,
                    "inferred_test_command": c.inferred_test_command,
                    "manifest_files": c.manifest_files,
                }
                for c in self.components
            ],
            "effective_build_matrix": {
                k: {
                    "working_directory": v.working_directory,
                    "build_command": v.build_command,
                    "test_command": v.test_command,
                }
                for k, v in self.effective_build_matrix.items()
            },
        }


class StackDetector:
    """
    Scans a workspace to identify languages, frameworks, and build scripts.
    """

    def __init__(self, workspace_path: Optional[Path] = None, config: Optional[DriftGuardConfig] = None):
        self.workspace_path = Path(workspace_path or Path.cwd()).resolve()
        self.config = config or DriftGuardConfig.load(self.workspace_path / ".driftguard.yml")

    def detect_stack(self) -> StackReport:
        """
        Inspect repository structure to detect components and apply overrides.
        """
        components: List[ComponentStack] = []
        languages: Set[str] = set()

        # Check root workspace
        root_components = self._inspect_directory(self.workspace_path, rel_path=".")
        components.extend(root_components)

        # Check subdirectories for potential monorepos/polyglot stacks
        # Check standard component directories: frontend, client, web, backend, server, api
        subdirs_to_check = ["frontend", "client", "web", "ui", "backend", "server", "api", "app"]
        for sub in subdirs_to_check:
            sub_dir = self.workspace_path / sub
            if sub_dir.is_dir():
                sub_comps = self._inspect_directory(sub_dir, rel_path=sub)
                # Avoid duplicating components already found at root
                for sc in sub_comps:
                    if not any(c.working_directory == sc.working_directory for c in components):
                        components.append(sc)

        for c in components:
            languages.add(c.primary_language)

        is_polyglot = len(languages) > 1 or len(components) > 1

        # Synthesize effective build matrix by combining auto-detection with config overrides
        effective_matrix: Dict[str, BuildTargetConfig] = {}

        if self.config.build_matrix.auto_detect:
            for c in components:
                effective_matrix[c.name] = BuildTargetConfig(
                    working_directory=c.working_directory,
                    build_command=c.inferred_build_command,
                    test_command=c.inferred_test_command,
                )

        # Apply overrides from .driftguard.yml
        for name, override in self.config.build_matrix.overrides.items():
            if name in effective_matrix:
                # Merge override into auto-detected target
                existing = effective_matrix[name]
                effective_matrix[name] = BuildTargetConfig(
                    working_directory=override.working_directory or existing.working_directory,
                    build_command=override.build_command or existing.build_command,
                    test_command=override.test_command or existing.test_command,
                )
            else:
                effective_matrix[name] = override

        return StackReport(
            workspace_path=str(self.workspace_path),
            is_polyglot=is_polyglot,
            components=components,
            detected_languages=sorted(languages),
            effective_build_matrix=effective_matrix,
        )

    def _inspect_directory(self, dir_path: Path, rel_path: str) -> List[ComponentStack]:
        """Inspect a specific directory for package manifests and frameworks."""
        components: List[ComponentStack] = []

        # 1. Node / JavaScript / TypeScript detection
        pkg_json = dir_path / "package.json"
        if pkg_json.is_file():
            comp = self._parse_node_package(dir_path, rel_path, pkg_json)
            if comp:
                components.append(comp)

        # 2. Python detection
        pyproject = dir_path / "pyproject.toml"
        requirements = dir_path / "requirements.txt"
        setup_py = dir_path / "setup.py"
        if pyproject.is_file() or requirements.is_file() or setup_py.is_file():
            comp = self._parse_python_project(dir_path, rel_path, pyproject, requirements, setup_py)
            if comp:
                components.append(comp)

        # 3. Rust detection
        cargo_toml = dir_path / "Cargo.toml"
        if cargo_toml.is_file():
            components.append(
                ComponentStack(
                    name=f"rust_{rel_path.replace('.', 'root')}",
                    working_directory=rel_path,
                    primary_language="Rust",
                    frameworks=["Cargo"],
                    package_manager="cargo",
                    inferred_build_command="cargo check && cargo build",
                    inferred_test_command="cargo test",
                    manifest_files=["Cargo.toml"],
                )
            )

        # 4. Go detection
        go_mod = dir_path / "go.mod"
        if go_mod.is_file():
            components.append(
                ComponentStack(
                    name=f"go_{rel_path.replace('.', 'root')}",
                    working_directory=rel_path,
                    primary_language="Go",
                    frameworks=["Go Modules"],
                    package_manager="go",
                    inferred_build_command="go build ./...",
                    inferred_test_command="go test ./...",
                    manifest_files=["go.mod"],
                )
            )

        return components

    def _parse_node_package(self, dir_path: Path, rel_path: str, pkg_json: Path) -> Optional[ComponentStack]:
        """Analyze package.json and lockfiles to infer framework and commands."""
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        scripts = data.get("scripts", {})
        frameworks = []

        is_ts = (dir_path / "tsconfig.json").is_file() or any(
            "typescript" in d for d in deps
        )
        lang = "TypeScript" if is_ts else "JavaScript"

        if "next" in deps:
            frameworks.append("Next.js")
        if "vite" in deps:
            frameworks.append("Vite")
        if "react" in deps:
            frameworks.append("React")
        if "vue" in deps:
            frameworks.append("Vue")
        if "express" in deps:
            frameworks.append("Express")

        # Detect package manager
        pm = "npm"
        if (dir_path / "pnpm-lock.yaml").is_file():
            pm = "pnpm"
        elif (dir_path / "yarn.lock").is_file():
            pm = "yarn"
        elif (dir_path / "bun.lockb").is_file():
            pm = "bun"

        # Infer build & test commands
        build_cmd = None
        if "build" in scripts:
            build_cmd = f"{pm} run build"

        test_cmd = None
        if "test" in scripts:
            test_cmd = f"{pm} test"
            if "react-scripts" in deps:
                test_cmd += " -- --watchAll=false"

        comp_name = "frontend" if ("frontend" in rel_path or "next" in deps or "react" in deps) else f"node_{rel_path.replace('.', 'root')}"

        return ComponentStack(
            name=comp_name,
            working_directory=rel_path,
            primary_language=lang,
            frameworks=frameworks or ["Node.js"],
            package_manager=pm,
            inferred_build_command=build_cmd,
            inferred_test_command=test_cmd,
            manifest_files=["package.json"],
        )

    def _parse_python_project(
        self,
        dir_path: Path,
        rel_path: str,
        pyproject: Path,
        requirements: Path,
        setup_py: Path,
    ) -> ComponentStack:
        """Analyze Python files to infer framework and commands."""
        frameworks = []
        manifests = []
        raw_text = ""

        if requirements.is_file():
            manifests.append("requirements.txt")
            raw_text += requirements.read_text(errors="replace").lower()
        if pyproject.is_file():
            manifests.append("pyproject.toml")
            raw_text += pyproject.read_text(errors="replace").lower()
        if setup_py.is_file():
            manifests.append("setup.py")
            raw_text += setup_py.read_text(errors="replace").lower()

        if "fastapi" in raw_text:
            frameworks.append("FastAPI")
        if "django" in raw_text:
            frameworks.append("Django")
        if "flask" in raw_text:
            frameworks.append("Flask")
        if "streamlit" in raw_text:
            frameworks.append("Streamlit")

        pm = "pip"
        if "poetry" in raw_text:
            pm = "poetry"

        build_cmd = "python -m py_compile **/*.py"
        test_cmd = "pytest tests/" if (dir_path / "tests").is_dir() or (self.workspace_path / "tests").is_dir() else "python -m unittest"

        comp_name = "backend" if ("backend" in rel_path or "api" in rel_path or rel_path == ".") else f"python_{rel_path.replace('.', 'root')}"

        return ComponentStack(
            name=comp_name,
            working_directory=rel_path,
            primary_language="Python",
            frameworks=frameworks or ["Python"],
            package_manager=pm,
            inferred_build_command=build_cmd,
            inferred_test_command=test_cmd,
            manifest_files=manifests,
        )

"""
DriftGuard Declarative Configuration Schema
Defines and validates repository-level policies loaded from .driftguard.yml.
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class BranchesConfig(BaseModel):
    """Target branch filtering configuration."""
    include: List[str] = Field(
        default_factory=lambda: ["main", "master", "develop", "release/*", "feature/*"],
        description="Glob patterns of branches to audit."
    )
    exclude: List[str] = Field(
        default_factory=lambda: ["docs-only/*", "gh-pages"],
        description="Glob patterns of branches to skip."
    )


class BuildTargetConfig(BaseModel):
    """Explicit build and test commands for a stack component."""
    working_directory: str = Field(default=".", description="Relative directory of the component.")
    build_command: Optional[str] = Field(default=None, description="Command to build/compile (e.g. npm run build).")
    test_command: Optional[str] = Field(default=None, description="Command to run tests (e.g. pytest).")


class BuildMatrixConfig(BaseModel):
    """Build matrix and autonomous detection configuration."""
    auto_detect: bool = Field(default=True, description="Autonomously detect stack and infer commands.")
    overrides: Dict[str, BuildTargetConfig] = Field(
        default_factory=dict,
        description="Component-specific overrides keyed by identifier (e.g. frontend, backend)."
    )


class SandboxConfig(BaseModel):
    """Ephemeral sandboxed execution environment settings."""
    runtime: str = Field(default="docker", description="Sandbox runtime: 'docker' or 'kubernetes'.")
    memory_limit: str = Field(default="2Gi", description="Maximum container memory limit.")
    cpu_limit: str = Field(default="2.0", description="Maximum container CPU limit.")
    timeout_seconds: int = Field(default=120, description="Build execution timeout in seconds.")
    network_access: str = Field(
        default="restricted",
        description="Egress policy: 'none', 'restricted' (package registries only), or 'unrestricted'."
    )


class RepairConfig(BaseModel):
    """Bounded self-healing and reflection loop configuration."""
    enabled: bool = Field(default=True, description="Enable automated patch synthesis and verification.")
    max_attempts: int = Field(default=3, description="Maximum iterative repair attempts to prevent infinite loops.")
    require_passing_tests: bool = Field(default=True, description="Require all tests to pass before accepting patch.")
    minimal_diff_only: bool = Field(default=True, description="Enforce Karpathy-style surgical diffs.")


class PullRequestConfig(BaseModel):
    """Pull request actuation and reviewer configuration."""
    auto_create: bool = Field(default=True, description="Automatically submit PR when patch passes sandbox.")
    target_branch_prefix: str = Field(default="driftguard/fix-", description="Prefix for automated fix branches.")
    labels: List[str] = Field(
        default_factory=lambda: ["driftguard", "automated-fix", "needs-review"],
        description="Labels attached to generated PR."
    )
    reviewers: List[str] = Field(default_factory=list, description="GitHub handles/teams to request review from.")


class ModelRoutingConfig(BaseModel):
    """Dynamic model routing tiers via OmniRoute."""
    auditing_tier: str = Field(default="fast", description="Model tier for inconsistency detection.")
    repair_tier: str = Field(default="deep", description="Model tier for patch synthesis & compiler reflection.")


class DriftGuardConfig(BaseModel):
    """Complete root DriftGuard repository policy configuration."""
    version: str = Field(default="1.0", description="Specification schema version.")
    branches: BranchesConfig = Field(default_factory=BranchesConfig)
    build_matrix: BuildMatrixConfig = Field(default_factory=BuildMatrixConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    repair: RepairConfig = Field(default_factory=RepairConfig)
    pull_request: PullRequestConfig = Field(default_factory=PullRequestConfig)
    model_routing: ModelRoutingConfig = Field(default_factory=ModelRoutingConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "DriftGuardConfig":
        """
        Load configuration from the specified file path, or search default root locations.
        Falls back to safe default configuration if no file is present.
        """
        target_path: Optional[Path] = None
        if path:
            target_path = Path(path)
        else:
            candidates = [Path(".driftguard.yml"), Path(".driftguard.yaml"), Path(".github/.driftguard.yml")]
            for c in candidates:
                if c.exists():
                    target_path = c
                    break

        if not target_path or not target_path.exists():
            return cls()

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse DriftGuard configuration from {target_path}: {e}") from e

    def to_yaml(self) -> str:
        """Serialize configuration to clean YAML."""
        return yaml.dump(self.model_dump(), sort_keys=False, default_flow_style=False)

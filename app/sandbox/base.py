"""Common contracts for isolated DriftGuard execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SandboxExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    status: str
    command: str

    def to_dict(self) -> dict:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "command": self.command,
        }


class SandboxRunner(ABC):
    def __init__(
        self,
        workspace_path: Path,
        timeout_seconds: int = 120,
        memory_limit: str = "2Gi",
        cpu_limit: str = "2.0",
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.sandbox_path: Optional[Path] = None

    @abstractmethod
    def provision(self) -> Path:
        """Create an isolated, writable workspace copy."""

    @abstractmethod
    def run_command(self, command: str, working_dir: Optional[str] = None) -> SandboxExecutionResult:
        """Run a command inside the isolated workspace."""

    @abstractmethod
    def apply_patch(self, unified_diff: str) -> bool:
        """Apply a unified diff to the isolated workspace."""

    @abstractmethod
    def cleanup(self) -> None:
        """Destroy the isolated workspace and any runtime resources."""

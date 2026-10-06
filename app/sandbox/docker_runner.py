"""Docker and local-process sandbox implementations."""

import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.config_schema import DriftGuardConfig
from app.sandbox.base import SandboxExecutionResult, SandboxRunner

logger = logging.getLogger(__name__)


def _safe_working_dir(root: Path, working_dir: Optional[str]) -> Path:
    root = root.resolve()
    if not working_dir or working_dir == ".":
        return root
    candidate = (root / working_dir).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Working directory escapes sandbox: {working_dir}")
    if not candidate.is_dir():
        raise ValueError(f"Working directory does not exist: {working_dir}")
    return candidate


def _result(command: str, started: float, exit_code: int, stdout: str, stderr: str, status: str) -> SandboxExecutionResult:
    return SandboxExecutionResult(exit_code, stdout, stderr, time.monotonic() - started, status, command)


class LocalProcessSandboxRunner(SandboxRunner):
    """Run commands in a temporary copy without touching the host checkout."""

    def provision(self) -> Path:
        if self.sandbox_path is None:
            self.sandbox_path = Path(tempfile.mkdtemp(prefix="driftguard_sandbox_"))
            destination = self.sandbox_path / self.workspace_path.name
            shutil.copytree(self.workspace_path, destination, ignore=shutil.ignore_patterns(".git"))
            self.sandbox_path = destination
        return self.sandbox_path

    def run_command(self, command: str, working_dir: Optional[str] = None) -> SandboxExecutionResult:
        root = self.provision()
        cwd = _safe_working_dir(root, working_dir)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            return _result(command, started, completed.returncode, completed.stdout, completed.stderr,
                           "SUCCESS" if completed.returncode == 0 else "FAILED")
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            return _result(command, started, 124, stdout, stderr, "TIMEOUT")
        except OSError as exc:
            return _result(command, started, 1, "", str(exc), "ERROR")

    def apply_patch(self, unified_diff: str) -> bool:
        root = self.provision()
        if not unified_diff.strip() or "\x00" in unified_diff:
            return False
        try:
            subprocess.run(
                ["git", "apply", "--check", "--whitespace=nowarn", "-"],
                cwd=root,
                input=unified_diff,
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "-"],
                cwd=root,
                input=unified_diff,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, OSError):
            return False

    def cleanup(self) -> None:
        if self.sandbox_path is not None:
            top = self.sandbox_path
            while top.parent.name.startswith("driftguard_sandbox_"):
                top = top.parent
            shutil.rmtree(top, ignore_errors=True)
            self.sandbox_path = None


class DockerSandboxRunner(LocalProcessSandboxRunner):
    """Use Docker for command execution while retaining a disposable copy."""

    def __init__(self, *args, image: str = "python:3.12-slim", network_access: str = "none", **kwargs):
        super().__init__(*args, **kwargs)
        self.image = image
        self.network_access = network_access

    def run_command(self, command: str, working_dir: Optional[str] = None) -> SandboxExecutionResult:
        root = self.provision()
        cwd = _safe_working_dir(root, working_dir)
        relative_cwd = "/workspace" if cwd == root else f"/workspace/{cwd.relative_to(root)}"
        network = "none" if self.network_access in ("none", "restricted") else "bridge"
        docker_command = [
            "docker", "run", "--rm", "--memory", self.memory_limit, "--cpus", self.cpu_limit,
            "--network", network, "--user", "1000:1000", "-v", f"{root}:/workspace:rw",
            "-w", relative_cwd, self.image, "sh", "-lc", command,
        ]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                docker_command, capture_output=True, text=True, timeout=self.timeout_seconds
            )
            return _result(command, started, completed.returncode, completed.stdout, completed.stderr,
                           "SUCCESS" if completed.returncode == 0 else "FAILED")
        except subprocess.TimeoutExpired as exc:
            return _result(command, started, 124, exc.stdout or "", exc.stderr or "", "TIMEOUT")
        except OSError as exc:
            return _result(command, started, 1, "", str(exc), "ERROR")


def get_sandbox_runner(workspace_path: Path, config: Optional[DriftGuardConfig] = None) -> SandboxRunner:
    cfg = config or DriftGuardConfig.load(Path(workspace_path) / ".driftguard.yml")
    kwargs = {
        "workspace_path": workspace_path,
        "timeout_seconds": cfg.sandbox.timeout_seconds,
        "memory_limit": cfg.sandbox.memory_limit,
        "cpu_limit": cfg.sandbox.cpu_limit,
    }
    if cfg.sandbox.runtime == "docker":
        try:
            subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=5)
            return DockerSandboxRunner(network_access=cfg.sandbox.network_access, **kwargs)
        except (OSError, subprocess.SubprocessError):
            logger.warning("Docker is unavailable; using an isolated local process sandbox.")
    return LocalProcessSandboxRunner(**kwargs)

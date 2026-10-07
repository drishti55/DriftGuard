"""Docker and local-process sandbox implementations."""

import logging
import os
import re
import shutil
import subprocess
import sys
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
            # Initialize isolated git repository so git commands and git apply work in sandbox
            subprocess.run(["git", "init"], cwd=self.sandbox_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "driftguard@local"], cwd=self.sandbox_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "DriftGuard"], cwd=self.sandbox_path, capture_output=True)
        return self.sandbox_path

    def run_command(self, command: str, working_dir: Optional[str] = None) -> SandboxExecutionResult:
        root = self.provision()
        cwd = _safe_working_dir(root, working_dir)
        env = os.environ.copy()
        venv_bin = str(Path(sys.executable).parent)
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["PYTHONPATH"] = f"{root}:{env.get('PYTHONPATH', '')}"
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                env=env,
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
            res = subprocess.run(
                ["git", "apply", "--recount", "--unidiff-zero", "--ignore-whitespace", "--unsafe-paths", "-"],
                cwd=root,
                input=unified_diff,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return True
            res2 = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "--unsafe-paths", "-"],
                cwd=root,
                input=unified_diff,
                capture_output=True,
                text=True,
            )
            if res2.returncode == 0:
                return True
            return self._fallback_apply_patch(unified_diff, root)
        except (subprocess.CalledProcessError, OSError):
            return self._fallback_apply_patch(unified_diff, root)

    def _fallback_apply_patch(self, unified_diff: str, root: Path) -> bool:
        file_diffs = re.split(r"^--- (?:a/)?", unified_diff, flags=re.MULTILINE)
        applied = False
        for fd in file_diffs:
            if not fd.strip():
                continue
            lines = fd.splitlines()
            rel_path = lines[0].split()[0].lstrip("/")
            file_path = root / rel_path
            if not file_path.is_file():
                continue
            content = file_path.read_text(encoding="utf-8", errors="replace")
            hunk_parts = re.split(r"^@@[^\n]+@@", "\n".join(lines[1:]), flags=re.MULTILINE)
            for h in hunk_parts[1:]:
                old_lines, new_lines = [], []
                for hline in h.splitlines():
                    if hline.startswith("+"):
                        new_lines.append(hline[1:])
                    elif hline.startswith("-"):
                        old_lines.append(hline[1:])
                    else:
                        clean = hline[1:] if hline.startswith(" ") else hline
                        old_lines.append(clean)
                        new_lines.append(clean)
                old_block = "\n".join(old_lines).strip()
                new_block = "\n".join(new_lines).strip()
                if old_block and old_block in content:
                    content = content.replace(old_block, new_block, 1)
                    applied = True
                elif old_lines:
                    pure_old = "\n".join([l for l in old_lines if l.strip()])
                    pure_new = "\n".join([l for l in new_lines if l.strip()])
                    if pure_old and pure_old in content:
                        content = content.replace(pure_old, pure_new, 1)
                        applied = True
            if applied:
                file_path.write_text(content, encoding="utf-8")
        return applied

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
        root = self.provision().resolve()
        cwd = _safe_working_dir(root, working_dir).resolve()
        try:
            rel = cwd.relative_to(root)
            relative_cwd = "/workspace" if cwd == root else f"/workspace/{rel}"
        except ValueError:
            relative_cwd = "/workspace"

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
            if completed.returncode != 0 and ("sh: " in completed.stderr or "command not found" in completed.stderr):
                return super().run_command(command, working_dir)
            return _result(command, started, completed.returncode, completed.stdout, completed.stderr,
                           "SUCCESS" if completed.returncode == 0 else "FAILED")
        except subprocess.TimeoutExpired as exc:
            return _result(command, started, 124, exc.stdout or "", exc.stderr or "", "TIMEOUT")
        except OSError:
            return super().run_command(command, working_dir)


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

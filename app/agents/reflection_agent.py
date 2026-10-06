"""Bounded compiler/test reflection for sandboxed repairs."""

from dataclasses import dataclass, field
from typing import Callable

from app.sandbox.base import SandboxExecutionResult


@dataclass
class RepairAttempt:
    attempt_number: int
    patch: str
    results: list[SandboxExecutionResult] = field(default_factory=list)
    utility_score: float = 0.0
    verified: bool = False

    def to_dict(self) -> dict:
        return {"attempt_number": self.attempt_number, "patch": self.patch,
                "results": [r.to_dict() for r in self.results], "utility_score": self.utility_score,
                "verified": self.verified}


@dataclass
class RepairReport:
    attempts: list[RepairAttempt] = field(default_factory=list)
    final_patch: str = ""
    verified: bool = False
    status: str = "FAILED"

    def to_dict(self) -> dict:
        return {"attempts": [a.to_dict() for a in self.attempts], "final_patch": self.final_patch,
                "verified": self.verified, "status": self.status}


def patch_utility_score(exit_code_success: float, passed_test_ratio: float, delta_churn: float, attempt_number: int,
                        w1: float = 1.0, w2: float = 1.0, w3: float = 0.5, w4: float = 0.1) -> float:
    return w1 * exit_code_success + w2 * passed_test_ratio - w3 * delta_churn - w4 * attempt_number


class CompilerReflectionAgent:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max(1, max_attempts)

    def build_reflection_prompt(self, patch: str, results: list[SandboxExecutionResult]) -> str:
        output = "\n".join(f"{r.command}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}" for r in results)
        return f"Previous patch:\n{patch}\n\nCompiler/test feedback:\n{output}\nReturn a revised minimal unified diff only."

    def score(self, results: list[SandboxExecutionResult], patch: str, attempt_number: int) -> float:
        if not results:
            return -0.1 * attempt_number
        passed = sum(result.exit_code == 0 for result in results)
        ratio = passed / len(results)
        churn = sum(line.startswith(("+", "-")) and not line.startswith(("+++", "---")) for line in patch.splitlines()) / max(len(patch.splitlines()), 1)
        return patch_utility_score(float(all(result.exit_code == 0 for result in results)), ratio, churn, attempt_number)

    def run(self, generate_and_execute: Callable[[str], tuple[str, list[SandboxExecutionResult]]], initial_context: str = "") -> RepairReport:
        report = RepairReport()
        context = initial_context
        patch = ""
        for attempt in range(1, self.max_attempts + 1):
            patch, results = generate_and_execute(context)
            verified = bool(results) and all(result.exit_code == 0 and result.status == "SUCCESS" for result in results)
            entry = RepairAttempt(attempt, patch, results, self.score(results, patch, attempt), verified)
            report.attempts.append(entry)
            report.final_patch = patch
            if verified:
                report.verified = True
                report.status = "VERIFIED"
                break
            context = self.build_reflection_prompt(patch, results)
        return report

"""Generate and validate surgical patches for confirmed drift."""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from app import config
from app.agents.drift_auditor import ConfirmedDrift
from app.analysis.llm_client import LLMClient
from app.config_schema import BuildTargetConfig
from app.sandbox.base import SandboxRunner

logger = logging.getLogger(__name__)
_DIFF_HEADER = re.compile(r"^--- a/([^\n]+)\n\+\+\+ b/([^\n]+)", re.MULTILINE)


@dataclass
class RepairCandidate:
    patch: str
    provider: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {"patch": self.patch, "provider": self.provider, "error": self.error}


class SandboxedRepairEngineer:
    def __init__(self, workspace_path: Path, omniroute_host: Optional[str] = None, api_key: Optional[str] = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.omniroute_host = omniroute_host or config.OMNIROUTE_HOST
        self.api_key = api_key or config.OMNIROUTE_API_KEY or os.getenv("OMNIROUTE_API_KEY", "")

    def build_prompt(self, drift: ConfirmedDrift, error_context: str = "") -> str:
        files = [drift.artifact_1_path, drift.artifact_2_path]
        contents = []
        for path in files:
            target = (self.workspace_path / path).resolve()
            if target.is_file() and self.workspace_path in target.parents:
                contents.append(f"\n### {path}\n{target.read_text(encoding='utf-8', errors='replace')[:config.MAX_CONTEXT_CHARS]}")
        return f"""You are DriftGuard's repair engineer. Fix only this confirmed drift.
Category: {drift.category}
Evidence 1: {drift.evidence_1}
Evidence 2: {drift.evidence_2}
Suggested fix: {drift.suggested_fix}
{''.join(contents)}
Previous compiler/test output (if any):
{error_context}

Return ONLY a standard unified diff beginning with --- a/<path> and +++ b/<path>.
Use repository-relative paths, change the smallest possible lines, and do not include Markdown fences or explanation."""

    def request_patch(self, prompt: str, model: Optional[str] = None) -> RepairCandidate:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": model or config.DEFAULT_MODEL, "messages": [
            {"role": "system", "content": "Output only a unified diff."},
            {"role": "user", "content": prompt},
        ], "temperature": 0.0}
        try:
            with httpx.Client(timeout=90.0) as client:
                response = client.post(f"{self.omniroute_host.rstrip('/')}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return RepairCandidate(self._clean_patch(content), f"omniroute/{payload['model']}")
        except Exception as exc:
            logger.debug("OmniRoute repair request failed: %s", exc)
        try:
            response = LLMClient(model=config.OLLAMA_MODEL).client.generate(
                model=config.OLLAMA_MODEL, prompt=prompt, options={"temperature": 0.0}
            )
            return RepairCandidate(self._clean_patch(response.get("response", "")), f"ollama/{config.OLLAMA_MODEL}")
        except Exception as exc:
            return RepairCandidate("", "none", str(exc))

    @staticmethod
    def _clean_patch(content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            return ""
        match = _DIFF_HEADER.search(content)
        return content[match.start():] if match else ""

    def validate_patch(self, patch: str, allowed_paths: set[str]) -> bool:
        matches = _DIFF_HEADER.findall(patch)
        if not matches or any(a != b or a not in allowed_paths or Path(a).is_absolute() or ".." in Path(a).parts for a, b in matches):
            return False
        return True

    def apply_and_validate(
        self,
        drift: ConfirmedDrift,
        runner: SandboxRunner,
        build_targets: dict[str, BuildTargetConfig],
        error_context: str = "",
        model: Optional[str] = None,
    ) -> tuple[RepairCandidate, list]:
        candidate = self.request_patch(self.build_prompt(drift, error_context), model)
        if not self.validate_patch(candidate.patch, {drift.artifact_1_path, drift.artifact_2_path}):
            candidate.error = candidate.error or "Model did not return an allowed unified diff."
            return candidate, []
        if not runner.apply_patch(candidate.patch):
            candidate.error = "Patch could not be applied in the sandbox."
            return candidate, []
        results = []
        for target in build_targets.values():
            for command in (target.build_command, target.test_command):
                if command:
                    results.append(runner.run_command(command, target.working_directory))
        return candidate, results

"""
DriftGuard Drift Detector
Orchestrates the full drift detection pipeline:
  Load artifacts → build prompt → call LLM → validate output → return report.
Supports both baseline (direct prompting) and RAG-enhanced modes.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict

from app import config
from app.analysis.llm_client import LLMClient
from app.analysis.prompts import build_baseline_prompt, build_rag_prompt
from app.analysis.output_validator import DriftPrediction, ParseResult
from app.analysis.evidence_verifier import EvidenceVerifier

logger = logging.getLogger(__name__)


@dataclass
class DriftReport:
    """Complete drift analysis report for a single artifact pair."""
    case_id: str = ""
    repository: str = ""
    artifact_1_path: str = ""
    artifact_1_type: str = ""
    artifact_2_path: str = ""
    artifact_2_type: str = ""
    prediction: Optional[DriftPrediction] = None
    parse_success: bool = False
    error: Optional[str] = None
    mode: str = "baseline"  # "baseline" or "rag"
    latency_s: float = 0.0
    raw_output: str = ""
    verification_status: str = "Not Evaluated"
    verification_details: str = ""
    real_evidence_1: str = ""
    real_evidence_2: str = ""

    def to_dict(self) -> dict:
        d = {
            "case_id": self.case_id,
            "repository": self.repository,
            "artifact_1_path": self.artifact_1_path,
            "artifact_1_type": self.artifact_1_type,
            "artifact_2_path": self.artifact_2_path,
            "artifact_2_type": self.artifact_2_type,
            "parse_success": self.parse_success,
            "error": self.error,
            "mode": self.mode,
            "latency_s": self.latency_s,
            "verification_status": self.verification_status,
            "verification_details": self.verification_details,
            "real_evidence_1": self.real_evidence_1,
            "real_evidence_2": self.real_evidence_2,
        }
        if self.prediction:
            d["prediction"] = self.prediction.model_dump()
        else:
            d["prediction"] = None
        return d


class DriftDetector:
    """
    Main drift detection engine.
    Loads file content from the local dataset and sends it through the LLM.
    """

    def __init__(self, llm_client: LLMClient = None, retriever=None):
        self.llm = llm_client or LLMClient()
        self.retriever = retriever  # Set for RAG mode
        self.verifier = EvidenceVerifier()
        self._clone_data = None

    def _load_clone_data(self) -> dict:
        """Load clone_results.json to resolve repo paths and commit SHAs."""
        if self._clone_data is None:
            if config.CLONE_RESULTS_JSON.exists():
                with open(config.CLONE_RESULTS_JSON) as f:
                    data = json.load(f)
                self._clone_data = {}
                for r in data.get("results", []):
                    self._clone_data[r["full_name"]] = r
            else:
                self._clone_data = {}
        return self._clone_data

    def _resolve_file_path(self, repository: str, file_path: str,
                           commit_sha: str = None) -> Optional[Path]:
        """
        Resolve a file path to an actual file on disk.
        Tries: snapshot dir (commit-specific) → repo dir → direct path.
        """
        clone_data = self._load_clone_data()

        # Try snapshot first (commit-specific)
        if commit_sha and repository in clone_data:
            repo_info = clone_data[repository]
            for snapshot in repo_info.get("snapshots", []):
                if snapshot.get("commit_sha", "").startswith(commit_sha[:8]):
                    snapshot_path = Path(snapshot["path"]) / file_path
                    if snapshot_path.exists():
                        return snapshot_path

        # Try the repo directory
        repo_dir_name = repository.replace("/", "_")
        repo_path = config.REPOS_DIR / repo_dir_name / file_path
        if repo_path.exists():
            return repo_path

        # Try snapshots directory with partial commit match
        if commit_sha:
            snapshot_dir_name = f"{repo_dir_name}_{commit_sha[:8]}"
            snapshot_path = config.SNAPSHOTS_DIR / snapshot_dir_name / file_path
            if snapshot_path.exists():
                return snapshot_path

        return None

    def _read_file_content(self, file_path: Path, max_chars: int = None) -> str:
        """Read file content with size limits."""
        max_chars = max_chars or config.MAX_CONTEXT_CHARS

        if not file_path.exists():
            return "[File not found]"

        if file_path.stat().st_size > config.MAX_FILE_SIZE_BYTES:
            # Read only the beginning for very large files
            try:
                with open(file_path, 'r', errors='replace') as f:
                    content = f.read(max_chars)
                return content + "\n... [truncated — file too large]"
            except Exception:
                return "[Could not read file]"

        try:
            with open(file_path, 'r', errors='replace') as f:
                content = f.read()
            if len(content) > max_chars:
                content = content[:max_chars] + "\n... [truncated]"
            return content
        except Exception:
            return "[Could not read file]"

    def analyze_case(self, case: dict, mode: str = "baseline") -> DriftReport:
        """
        Analyze a single case from the dataset.

        Args:
            case: A dict from train/val/test JSONL with repository, artifact_1, artifact_2, etc.
            mode: "baseline" for direct prompting, "rag" for retrieval-augmented.

        Returns:
            DriftReport with prediction and metadata.
        """
        import time

        repository = case.get("repository", "")
        commit_sha = case.get("commit_sha", "")
        a1 = case.get("artifact_1", {})
        a2 = case.get("artifact_2", {})
        a1_path = a1.get("path", "")
        a1_type = a1.get("type", "")
        a2_path = a2.get("path", "")
        a2_type = a2.get("type", "")

        report = DriftReport(
            case_id=case.get("case_id", ""),
            repository=repository,
            artifact_1_path=a1_path,
            artifact_1_type=a1_type,
            artifact_2_path=a2_path,
            artifact_2_type=a2_type,
            mode=mode,
        )

        # Resolve and read file contents
        a1_file = self._resolve_file_path(repository, a1_path, commit_sha)
        a2_file = self._resolve_file_path(repository, a2_path, commit_sha)

        a1_content = self._read_file_content(a1_file) if a1_file else "[File not found on disk]"
        a2_content = self._read_file_content(a2_file) if a2_file else "[File not found on disk]"

        # Build prompt
        start_time = time.time()

        if mode == "rag" and self.retriever is not None:
            # Retrieve related context
            retrieved_context = self.retriever.retrieve_context(
                repository=repository,
                artifact_1_path=a1_path,
                artifact_1_type=a1_type,
                artifact_2_path=a2_path,
                artifact_2_type=a2_type,
            )
            prompt = build_rag_prompt(
                a1_path, a1_type, a1_content,
                a2_path, a2_type, a2_content,
                retrieved_context,
            )
        else:
            prompt = build_baseline_prompt(
                a1_path, a1_type, a1_content,
                a2_path, a2_type, a2_content,
            )

        # Call LLM
        result: ParseResult = self.llm.generate(prompt)
        elapsed = time.time() - start_time

        report.latency_s = elapsed
        report.raw_output = result.raw_output
        report.parse_success = result.success

        if result.success:
            report.prediction = result.prediction
            # Independently verify the evidence against the real repository files
            verification_result = self.verifier.verify(
                result.prediction,
                a1_content,
                a2_content
            )
            report.verification_status = verification_result.status
            report.verification_details = verification_result.details
            report.real_evidence_1 = verification_result.real_evidence_1
            report.real_evidence_2 = verification_result.real_evidence_2
        else:
            report.error = result.error
            report.verification_status = "Analysis Failed"
            report.verification_details = f"LLM parse failed: {result.error}"
            logger.warning(f"Case {report.case_id}: Parse failed — {result.error}")

        return report

    def analyze_cases(self, cases: List[dict], mode: str = "baseline",
                      progress_callback=None) -> List[DriftReport]:
        """
        Analyze a batch of cases.

        Args:
            cases: List of case dicts from JSONL
            mode: "baseline" or "rag"
            progress_callback: Optional callable(current, total, report) for progress tracking

        Returns:
            List of DriftReport objects
        """
        reports = []
        total = len(cases)

        for i, case in enumerate(cases):
            report = self.analyze_case(case, mode=mode)
            reports.append(report)

            if progress_callback:
                progress_callback(i + 1, total, report)

            if (i + 1) % 10 == 0:
                stats = self.llm.get_stats()
                logger.info(
                    f"Progress: {i + 1}/{total} | "
                    f"Parse rate: {stats['parse_success_rate']:.1%} | "
                    f"Avg latency: {stats['avg_latency_s']:.1f}s"
                )

        return reports

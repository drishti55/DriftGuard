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
    """Complete drift analysis report for a single artifact pair with full audit trace."""
    case_id: str = ""
    experiment_id: str = ""
    repository: str = ""
    repository_url: str = ""
    commit_sha: str = ""
    language: str = ""
    dataset_split: str = ""
    model: str = ""
    artifact_1_path: str = ""
    artifact_1_type: str = ""
    artifact_2_path: str = ""
    artifact_2_type: str = ""
    prediction: Optional[DriftPrediction] = None
    parse_success: bool = False
    error: Optional[str] = None
    mode: str = "baseline"  # "baseline" or "rag"
    prompt: str = ""
    retrieved_context: str = ""
    latency_s: float = 0.0
    raw_output: str = ""
    verification_status: str = "Not Evaluated"
    verification_details: str = ""
    real_evidence_1: str = ""
    real_evidence_2: str = ""
    execution_status: str = "COMPLETED"  # "COMPLETED", "FAILED", "FILE_NOT_FOUND", "REPOSITORY_UNAVAILABLE"
    ground_truth: Optional[dict] = None
    evaluation: Optional[dict] = None
    timestamp: str = ""

    def to_dict(self) -> dict:
        d = {
            "case_id": self.case_id,
            "experiment_id": self.experiment_id,
            "repository": self.repository,
            "repository_url": self.repository_url,
            "commit_sha": self.commit_sha,
            "language": self.language,
            "dataset_split": self.dataset_split,
            "model": self.model,
            "artifact_1_path": self.artifact_1_path,
            "artifact_1_type": self.artifact_1_type,
            "artifact_2_path": self.artifact_2_path,
            "artifact_2_type": self.artifact_2_type,
            "parse_success": self.parse_success,
            "error": self.error,
            "mode": self.mode,
            "prompt": self.prompt,
            "retrieved_context": self.retrieved_context,
            "latency_s": self.latency_s,
            "raw_output": self.raw_output,
            "verification_status": self.verification_status,
            "verification_details": self.verification_details,
            "real_evidence_1": self.real_evidence_1,
            "real_evidence_2": self.real_evidence_2,
            "execution_status": self.execution_status,
            "ground_truth": self.ground_truth,
            "evaluation": self.evaluation,
            "timestamp": self.timestamp,
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

    def _check_repo_status(self, repository: str, commit_sha: str = None) -> tuple[bool, str]:
        """Check if repository files or snapshot exist on disk."""
        repo_dir_name = repository.replace("/", "_")
        if commit_sha:
            snapshot_dir = config.SNAPSHOTS_DIR / f"{repo_dir_name}_{commit_sha[:8]}"
            if snapshot_dir.exists():
                return True, "SNAPSHOT_FOUND"
        matching_snapshots = list(config.SNAPSHOTS_DIR.glob(f"{repo_dir_name}_*"))
        if matching_snapshots:
            return True, "SNAPSHOT_FOUND"
        if (config.REPOS_DIR / repo_dir_name).exists():
            return True, "REPO_FOUND"
        return False, "REPOSITORY_UNAVAILABLE"

    def _resolve_file_path(self, repository: str, file_path: str,
                           commit_sha: str = None) -> Optional[Path]:
        """
        Resolve a file path to an actual file on disk.
        Tries: snapshot dir (commit-specific) → repo dir → glob snapshots.
        """
        clone_data = self._load_clone_data()

        # Try snapshot first (commit-specific from clone data)
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

        # Try snapshots directory with exact prefix
        if commit_sha:
            snapshot_dir_name = f"{repo_dir_name}_{commit_sha[:8]}"
            snapshot_path = config.SNAPSHOTS_DIR / snapshot_dir_name / file_path
            if snapshot_path.exists():
                return snapshot_path

        # Fallback: check any snapshot for that repository
        for snap_dir in config.SNAPSHOTS_DIR.glob(f"{repo_dir_name}_*"):
            cand = snap_dir / file_path
            if cand.exists():
                return cand

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

    def analyze_case(self, case: dict, mode: str = "baseline",
                     experiment_id: str = "") -> DriftReport:
        """
        Analyze a single case from the dataset.

        Args:
            case: A dict from train/val/test JSONL with repository, artifact_1, artifact_2, etc.
            mode: "baseline" for direct prompting, "rag" for retrieval-augmented.
            experiment_id: ID of the running experiment.

        Returns:
            DriftReport with prediction and metadata.
        """
        import time
        from datetime import datetime

        repository = case.get("repository", "")
        commit_sha = case.get("commit_sha", "")
        a1 = case.get("artifact_1", {})
        a2 = case.get("artifact_2", {})
        a1_path = a1.get("path", "")
        a1_type = a1.get("type", "")
        a2_path = a2.get("path", "")
        a2_type = a2.get("type", "")

        gt_drift = case.get("drift_present")
        gt_type = case.get("drift_type")

        report = DriftReport(
            case_id=case.get("case_id", ""),
            experiment_id=experiment_id,
            repository=repository,
            repository_url=case.get("repository_url", ""),
            commit_sha=commit_sha,
            language=case.get("language", ""),
            dataset_split=case.get("dataset_split", ""),
            model=getattr(self.llm, "model", ""),
            artifact_1_path=a1_path,
            artifact_1_type=a1_type,
            artifact_2_path=a2_path,
            artifact_2_type=a2_type,
            mode=mode,
            ground_truth=case,
            timestamp=datetime.now().isoformat(),
        )

        # Check repository availability
        has_repo, _ = self._check_repo_status(repository, commit_sha)
        if not has_repo:
            report.execution_status = "REPOSITORY_UNAVAILABLE"
            report.error = f"Repository snapshot not found on disk for {repository}"
            report.verification_status = "Analysis Incomplete"
            report.verification_details = report.error
            report.evaluation = {
                "ground_truth_drift": gt_drift,
                "ground_truth_type": gt_type,
                "predicted_drift": None,
                "predicted_type": None,
                "classification": "REPOSITORY_UNAVAILABLE",
                "failure_reason": "REPOSITORY_UNAVAILABLE"
            }
            return report

        # Resolve files on disk
        a1_file = self._resolve_file_path(repository, a1_path, commit_sha)
        a2_file = self._resolve_file_path(repository, a2_path, commit_sha)

        if not a1_file or not a2_file:
            missing = []
            if not a1_file: missing.append(f"artifact_1 ({a1_path})")
            if not a2_file: missing.append(f"artifact_2 ({a2_path})")
            report.execution_status = "FILE_NOT_FOUND"
            report.error = f"Artifact file not found: {', '.join(missing)}"
            report.verification_status = "Analysis Incomplete"
            report.verification_details = report.error
            report.evaluation = {
                "ground_truth_drift": gt_drift,
                "ground_truth_type": gt_type,
                "predicted_drift": None,
                "predicted_type": None,
                "classification": "FILE_NOT_FOUND",
                "failure_reason": "FILE_NOT_FOUND"
            }
            return report

        a1_content = self._read_file_content(a1_file)
        a2_content = self._read_file_content(a2_file)

        # Build prompt
        start_time = time.time()
        retrieved_context = ""

        if mode == "rag" and self.retriever is not None:
            retrieved_context = self.retriever.retrieve_context(
                repository=repository,
                artifact_1_path=a1_path,
                artifact_1_type=a1_type,
                artifact_2_path=a2_path,
                artifact_2_type=a2_type,
            )
            report.retrieved_context = retrieved_context
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

        report.prompt = prompt

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
            report.execution_status = "COMPLETED"

            pred_drift = result.prediction.drift_present
            pred_type = result.prediction.drift_type

            if gt_drift is not None:
                if pred_drift and gt_drift:
                    classification = "TRUE_POSITIVE"
                elif pred_drift and not gt_drift:
                    classification = "FALSE_POSITIVE"
                elif not pred_drift and not gt_drift:
                    classification = "TRUE_NEGATIVE"
                else:
                    classification = "FALSE_NEGATIVE"

                report.evaluation = {
                    "ground_truth_drift": gt_drift,
                    "ground_truth_type": gt_type,
                    "predicted_drift": pred_drift,
                    "predicted_type": pred_type,
                    "classification": classification,
                    "correct_type": (pred_type == gt_type) if (pred_drift and gt_drift) else None,
                    "verification_status": report.verification_status,
                    "evidence_verified": report.verification_status == "Confirmed Drift",
                    "failure_reason": None,
                }
        else:
            report.error = result.error
            report.execution_status = "FAILED"
            report.verification_status = "Analysis Failed"
            report.verification_details = f"LLM parse failed: {result.error}"
            report.evaluation = {
                "ground_truth_drift": gt_drift,
                "ground_truth_type": gt_type,
                "predicted_drift": None,
                "predicted_type": None,
                "classification": "ANALYSIS_ERROR",
                "failure_reason": f"PARSE_ERROR: {result.error}",
            }
            logger.warning(f"Case {report.case_id}: Parse failed — {result.error}")

        return report

    def analyze_cases(self, cases: List[dict], mode: str = "baseline",
                      progress_callback=None, case_callback=None,
                      experiment_id: str = "") -> List[DriftReport]:
        """
        Analyze a batch of cases with immediate per-case callback.

        Args:
            cases: List of case dicts from JSONL
            mode: "baseline" or "rag"
            progress_callback: Optional callable(current, total, report)
            case_callback: Optional callable(report) called immediately on completion
            experiment_id: Experiment ID for tracking

        Returns:
            List of DriftReport objects
        """
        reports = []
        total = len(cases)

        for i, case in enumerate(cases):
            report = self.analyze_case(case, mode=mode, experiment_id=experiment_id)
            reports.append(report)

            if case_callback:
                case_callback(report)

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

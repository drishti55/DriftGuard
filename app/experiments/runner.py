import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from collections import defaultdict

from app.experiments.config import ExperimentConfig, ExperimentResult
from app.analysis.llm_client import LLMClient
from app.analysis.drift_detector import DriftDetector, DriftReport
from app.evaluation.metrics import (
    compute_detection_metrics,
    compute_classification_metrics,
    compute_evidence_quality,
)
from app.utils.repo_utils import normalize_repository_name

logger = logging.getLogger(__name__)

class ExperimentRunner:
    """Runs DriftGuard experiments based on a configuration with full auditability and resumability."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_dataset_cases(self, config: ExperimentConfig) -> List[dict]:
        """Loads cases from the specified dataset split for the repository."""
        from app.config import SPLITS_DIR
        split_file = SPLITS_DIR / f"{config.dataset_split.lower()}.jsonl"
        
        target_repo = normalize_repository_name(config.repository).lower()
        is_all_repos = not config.repository or target_repo in ("all", "dataset: all", "")
        
        cases = []
        if split_file.exists():
            with open(split_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    case = json.loads(line)
                    case_repo = normalize_repository_name(case.get("repository", "")).lower()
                    if is_all_repos or case_repo == target_repo:
                        cases.append(case)
        return cases

    def get_experiment_cases(self, experiment_id: str) -> List[dict]:
        """Loads all individual case results for a specific experiment."""
        run_dir = self.storage_dir / experiment_id
        cases_file = run_dir / "cases.jsonl"
        reports_file = run_dir / "reports.jsonl"
        
        target_file = cases_file if cases_file.exists() else reports_file
        cases = []
        if target_file.exists():
            with open(target_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            cases.append(json.loads(line))
                        except Exception as e:
                            logger.error(f"Error parsing case line in {target_file}: {e}")
        return cases

    def run(self, config: ExperimentConfig, 
            cases_override: Optional[List[dict]] = None,
            progress_callback: Optional[Callable] = None) -> ExperimentResult:
        """Executes the experiment pipeline with resumability and audit logging."""
        logger.info(f"Starting experiment {config.experiment_id} with model {config.model}")
        
        run_dir = self.storage_dir / config.experiment_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save initial config
        with open(run_dir / "config.json", "w") as f:
            f.write(config.to_json())
            
        # 1. Validate Model Availability
        llm = LLMClient(model=config.model)
        if not llm.check_model_available(config.model):
            msg = f"Model {config.model} is not available in Ollama."
            logger.error(msg)
            failed_res = ExperimentResult(
                experiment_id=config.experiment_id,
                config=config,
                status="NOT RUN / MODEL UNAVAILABLE",
                status_reason=msg,
                total_cases_analyzed=0,
                total_failed=1
            )
            self.save_result(failed_res, [])
            return failed_res

        # 2. Setup Detector & RAG
        mode = "baseline" if config.rag_mode == "Non-RAG" else "rag"
        retriever = None
        
        if mode == "rag":
            from app.retrieval.vector_store import VectorStore
            from app.retrieval.retriever import Retriever
            from app.ingestion.repository_loader import RepositoryLoader
            vector_store = VectorStore()
            repo_loader = RepositoryLoader()
            retriever = Retriever(vector_store=vector_store, repo_loader=repo_loader)
            
        detector = DriftDetector(llm_client=llm, retriever=retriever)
        
        # 3. Load Cases
        cases = cases_override if cases_override is not None else self._load_dataset_cases(config)
        total_in_dataset = len(cases)
        
        if config.debug_sample_mode:
            cases = cases[:5]
            
        total_to_evaluate = len(cases)
        
        # 4. Resume Checkpointing
        cases_file = run_dir / "cases.jsonl"
        reports_file = run_dir / "reports.jsonl"
        
        completed_dict: Dict[str, dict] = {}
        if cases_file.exists():
            with open(cases_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            cid = d.get("case_id")
                            if cid and d.get("execution_status") in ("COMPLETED", "FILE_NOT_FOUND", "REPOSITORY_UNAVAILABLE"):
                                completed_dict[cid] = d
                        except Exception:
                            pass

        reports: List[DriftReport] = []
        
        # Open append streams for immediate case flushing
        cases_fp = open(cases_file, "a")
        reports_fp = open(reports_file, "a")
        
        try:
            for idx, case in enumerate(cases):
                cid = case.get("case_id", f"case_{idx}")
                
                # Check if already completed
                if cid in completed_dict:
                    cached_d = completed_dict[cid]
                    # Create report from cached
                    rep = DriftReport(
                        case_id=cached_d.get("case_id", ""),
                        experiment_id=cached_d.get("experiment_id", config.experiment_id),
                        repository=cached_d.get("repository", ""),
                        repository_url=cached_d.get("repository_url", ""),
                        commit_sha=cached_d.get("commit_sha", ""),
                        language=cached_d.get("language", ""),
                        dataset_split=cached_d.get("dataset_split", config.dataset_split),
                        model=cached_d.get("model", config.model),
                        artifact_1_path=cached_d.get("artifact_1_path", ""),
                        artifact_1_type=cached_d.get("artifact_1_type", ""),
                        artifact_2_path=cached_d.get("artifact_2_path", ""),
                        artifact_2_type=cached_d.get("artifact_2_type", ""),
                        parse_success=cached_d.get("parse_success", False),
                        error=cached_d.get("error"),
                        mode=cached_d.get("mode", mode),
                        prompt=cached_d.get("prompt", ""),
                        retrieved_context=cached_d.get("retrieved_context", ""),
                        latency_s=cached_d.get("latency_s", 0.0),
                        raw_output=cached_d.get("raw_output", ""),
                        verification_status=cached_d.get("verification_status", "Not Evaluated"),
                        verification_details=cached_d.get("verification_details", ""),
                        real_evidence_1=cached_d.get("real_evidence_1", ""),
                        real_evidence_2=cached_d.get("real_evidence_2", ""),
                        execution_status=cached_d.get("execution_status", "COMPLETED"),
                        ground_truth=cached_d.get("ground_truth"),
                        evaluation=cached_d.get("evaluation"),
                        timestamp=cached_d.get("timestamp", ""),
                    )
                    reports.append(rep)
                    if progress_callback:
                        progress_callback(idx + 1, total_to_evaluate, rep)
                    continue

                # Run fresh analysis
                report = detector.analyze_case(case, mode=mode, experiment_id=config.experiment_id)
                reports.append(report)
                
                # Immediate append & flush
                rep_dict = report.to_dict()
                cases_fp.write(json.dumps(rep_dict) + "\n")
                cases_fp.flush()
                reports_fp.write(json.dumps(rep_dict) + "\n")
                reports_fp.flush()
                
                if progress_callback:
                    progress_callback(idx + 1, total_to_evaluate, report)
        finally:
            cases_fp.close()
            reports_fp.close()

        # 5. Compute Comprehensive Metrics
        metrics_res = self._compute_all_metrics(cases, reports, config)
        
        stats = llm.get_stats()
        avg_lat = stats.get("avg_latency_s", 0.0)
        if avg_lat == 0.0 and reports:
            valid_latencies = [r.latency_s for r in reports if r.latency_s > 0]
            avg_lat = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0.0

        result = ExperimentResult(
            experiment_id=config.experiment_id,
            config=config,
            accuracy=metrics_res.get("accuracy"),
            f1_score=metrics_res.get("f1"),
            precision=metrics_res.get("precision"),
            recall=metrics_res.get("recall"),
            macro_f1=metrics_res.get("macro_f1"),
            false_positive_rate=metrics_res.get("false_positive_rate"),
            false_negative_rate=metrics_res.get("false_negative_rate"),
            confusion_matrix=metrics_res.get("confusion_matrix"),
            drift_type_metrics=metrics_res.get("drift_type_metrics"),
            repository_metrics=metrics_res.get("repository_metrics"),
            language_metrics=metrics_res.get("language_metrics"),
            evidence_accuracy=metrics_res.get("evidence_accuracy"),
            avg_latency_s=avg_lat,
            total_cases_analyzed=metrics_res.get("total_cases_analyzed", 0),
            total_cases_in_dataset=total_in_dataset,
            total_completed=metrics_res.get("total_completed", 0),
            total_failed=metrics_res.get("total_failed", 0),
            total_unavailable=metrics_res.get("total_unavailable", 0),
            status="COMPLETED",
        )
        
        # 6. Save final summary files
        self.save_result(result, reports)
        return result

    def _compute_all_metrics(self, cases: List[dict], reports: List[DriftReport], 
                            config: ExperimentConfig) -> Dict[str, Any]:
        """Calculates multi-dimensional metrics across all valid cases."""
        valid_pairs = []
        total_completed = 0
        total_failed = 0
        total_unavailable = 0
        
        for c, r in zip(cases, reports):
            if r.execution_status in ("FILE_NOT_FOUND", "REPOSITORY_UNAVAILABLE"):
                total_unavailable += 1
            elif r.execution_status == "FAILED" or not r.parse_success:
                total_failed += 1
            elif r.execution_status == "COMPLETED":
                total_completed += 1
                valid_pairs.append((c, r))
                
        if not valid_pairs:
            return {
                "accuracy": None,
                "f1": None,
                "precision": None,
                "recall": None,
                "macro_f1": None,
                "false_positive_rate": None,
                "false_negative_rate": None,
                "confusion_matrix": None,
                "drift_type_metrics": {},
                "repository_metrics": {},
                "language_metrics": {},
                "evidence_accuracy": None,
                "total_cases_analyzed": 0,
                "total_completed": total_completed,
                "total_failed": total_failed,
                "total_unavailable": total_unavailable,
            }
            
        y_true = []
        y_pred = []
        y_true_types = []
        y_pred_types = []
        
        # Groupings for breakdown
        by_repo = defaultdict(lambda: {"true": [], "pred": [], "cases": 0})
        by_lang = defaultdict(lambda: {"true": [], "pred": [], "cases": 0})
        by_type = defaultdict(lambda: {"true": [], "pred": [], "cases": 0})
        
        evidence_matches = 0
        evidence_total = 0
        
        for c, r in valid_pairs:
            t = bool(c.get("drift_present", False))
            gt_type = str(c.get("drift_type", "unknown"))
            repo = str(c.get("repository", "unknown"))
            lang = str(c.get("language", "unknown"))
            
            if config.enable_evidence_verification:
                if r.verification_status == "Confirmed Drift":
                    p = True
                elif r.prediction and r.prediction.drift_present:
                    p = not t  # penalize hallucination
                else:
                    p = False
            else:
                p = bool(r.prediction.drift_present) if r.prediction else False
                
            pred_type = str(r.prediction.drift_type) if (r.prediction and r.prediction.drift_type) else "no_drift"
            
            y_true.append(t)
            y_pred.append(p)
            y_true_types.append(gt_type)
            y_pred_types.append(pred_type)
            
            # Repo grouping
            by_repo[repo]["true"].append(t)
            by_repo[repo]["pred"].append(p)
            by_repo[repo]["cases"] += 1
            by_repo[repo]["language"] = lang
            
            # Lang grouping
            by_lang[lang]["true"].append(t)
            by_lang[lang]["pred"].append(p)
            by_lang[lang]["cases"] += 1
            
            # Type grouping
            by_type[gt_type]["true"].append(t)
            by_type[gt_type]["pred"].append(p)
            by_type[gt_type]["cases"] += 1
            
            if r.prediction and r.prediction.drift_present:
                evidence_total += 1
                if r.verification_status == "Confirmed Drift":
                    evidence_matches += 1

        det_metrics = compute_detection_metrics(y_true, y_pred)
        type_metrics = compute_classification_metrics(y_true_types, y_pred_types)
        
        # Per-repo summary
        repo_res = {}
        for rk, rv in by_repo.items():
            rm = compute_detection_metrics(rv["true"], rv["pred"])
            repo_res[rk] = {
                "accuracy": rm.get("accuracy"),
                "precision": rm.get("precision"),
                "recall": rm.get("recall"),
                "f1": rm.get("f1"),
                "cases": rv["cases"],
                "language": rv.get("language", "")
            }
            
        # Per-language summary
        lang_res = {}
        for lk, lv in by_lang.items():
            lm = compute_detection_metrics(lv["true"], lv["pred"])
            lang_res[lk] = {
                "accuracy": lm.get("accuracy"),
                "precision": lm.get("precision"),
                "recall": lm.get("recall"),
                "f1": lm.get("f1"),
                "cases": lv["cases"]
            }
            
        # Per-drift-type summary
        dt_res = {}
        for tk, tv in by_type.items():
            tm = compute_detection_metrics(tv["true"], tv["pred"])
            dt_res[tk] = {
                "accuracy": tm.get("accuracy"),
                "precision": tm.get("precision"),
                "recall": tm.get("recall"),
                "f1": tm.get("f1"),
                "cases": tv["cases"]
            }
            
        ev_acc = round(evidence_matches / evidence_total, 4) if evidence_total > 0 else None
        
        return {
            "accuracy": det_metrics.get("accuracy"),
            "f1": det_metrics.get("f1"),
            "precision": det_metrics.get("precision"),
            "recall": det_metrics.get("recall"),
            "macro_f1": type_metrics.get("macro_f1", det_metrics.get("f1")),
            "false_positive_rate": det_metrics.get("false_positive_rate"),
            "false_negative_rate": det_metrics.get("false_negative_rate"),
            "confusion_matrix": {
                "tp": det_metrics.get("true_positives", 0),
                "fp": det_metrics.get("false_positives", 0),
                "tn": det_metrics.get("true_negatives", 0),
                "fn": det_metrics.get("false_negatives", 0),
            },
            "drift_type_metrics": dt_res,
            "repository_metrics": repo_res,
            "language_metrics": lang_res,
            "evidence_accuracy": ev_acc,
            "total_cases_analyzed": len(valid_pairs),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "total_unavailable": total_unavailable,
        }

    def save_result(self, result: ExperimentResult, reports: List[DriftReport]):
        """Saves configuration, summary, and backward-compatible result.json."""
        run_dir = self.storage_dir / result.experiment_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        with open(run_dir / "config.json", "w") as f:
            f.write(result.config.to_json())
            
        with open(run_dir / "summary.json", "w") as f:
            f.write(result.to_json())
            
        # Keep result.json for backward compatibility
        with open(run_dir / "result.json", "w") as f:
            f.write(result.to_json())
            
        # Write reports.jsonl if reports passed
        if reports:
            with open(run_dir / "reports.jsonl", "w") as f:
                for r in reports:
                    f.write(json.dumps(r.to_dict()) + "\n")
                    
    def get_experiments(self) -> List[ExperimentResult]:
        """Loads all saved experiments with safe parsing and no fake zeroes."""
        results = []
        if self.storage_dir.exists():
            for d in self.storage_dir.iterdir():
                if d.is_dir():
                    summary_file = d / "summary.json"
                    res_file = d / "result.json"
                    target = summary_file if summary_file.exists() else res_file
                    if target.exists():
                        try:
                            with open(target, "r") as f:
                                data = json.load(f)
                                results.append(ExperimentResult.from_dict(data))
                        except Exception as e:
                            logger.error(f"Failed to load experiment {d.name}: {e}")
        return sorted(results, key=lambda x: x.timestamp, reverse=True)


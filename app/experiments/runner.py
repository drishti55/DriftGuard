import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Callable

from app.experiments.config import ExperimentConfig, ExperimentResult
from app.analysis.llm_client import LLMClient
from app.analysis.drift_detector import DriftDetector, DriftReport
from app.evaluation.metrics import compute_detection_metrics
from app.utils.repo_utils import normalize_repository_name

logger = logging.getLogger(__name__)

class ExperimentRunner:
    """Runs DriftGuard experiments based on a configuration."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_dataset_cases(self, config: ExperimentConfig) -> List[dict]:
        """Loads cases from the specified dataset split for the repo."""
        # This will be properly integrated with dataset loader logic
        # For now, it's a placeholder returning mock or dynamic runtime cases
        # In actual implementation, it would read from driftguard-dataset/splits/...
        from app.config import METADATA_DIR, SPLITS_DIR
        split_file = SPLITS_DIR / f"{config.dataset_split.lower()}.jsonl"
        
        target_repo = normalize_repository_name(config.repository).lower()
        is_all_repos = not config.repository or target_repo in ("all", "dataset: all", "")
        
        cases = []
        if split_file.exists():
            with open(split_file, "r") as f:
                for line in f:
                    case = json.loads(line)
                    case_repo = normalize_repository_name(case.get("repository", "")).lower()
                    if is_all_repos or case_repo == target_repo:
                        cases.append(case)
        return cases

    def run(self, config: ExperimentConfig, 
            cases_override: Optional[List[dict]] = None,
            progress_callback: Optional[Callable] = None) -> ExperimentResult:
        """Executes the experiment pipeline."""
        
        logger.info(f"Starting experiment {config.experiment_id} with model {config.model}")
        
        # 1. Setup Models & Detector
        llm = LLMClient(model=config.model)
        
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
        
        # 2. Get Cases
        cases = cases_override if cases_override else self._load_dataset_cases(config)
        if config.max_cases > 0:
            cases = cases[:config.max_cases]
            
        # 3. Analyze
        reports = detector.analyze_cases(
            cases=cases, 
            mode=mode, 
            progress_callback=progress_callback
        )
        
        # 4. Calculate Metrics (if ground truth available)
        # Filter out cases with Analysis Error or Failed from metrics
        valid_cases = []
        valid_reports = []
        for c, r in zip(cases, reports):
            if r.verification_status not in ("Analysis Error", "Analysis Failed") and r.parse_success:
                valid_cases.append(c)
                valid_reports.append(r)
                
        if not valid_cases:
            metrics = {}
        else:
            y_true = [c.get("drift_present", False) for c in valid_cases]
            if config.enable_evidence_verification:
                y_pred = [True if r.verification_status == "Confirmed Drift" else False for r in valid_reports]
            else:
                y_pred = [r.prediction.drift_present if r.prediction else False for r in valid_reports]
            metrics = compute_detection_metrics(y_true, y_pred) if "drift_present" in valid_cases[0] else {}
        
        # 5. Build Result
        stats = llm.get_stats()
        
        if "error" in metrics or not metrics:
            f1, prec, rec, macro, fpr = None, None, None, None, None
        else:
            f1 = metrics.get("f1")
            prec = metrics.get("precision")
            rec = metrics.get("recall")
            macro = metrics.get("f1")
            fpr = metrics.get("false_positive_rate")
            
        result = ExperimentResult(
            experiment_id=config.experiment_id,
            config=config,
            f1_score=f1,
            precision=prec,
            recall=rec,
            macro_f1=macro,
            false_positive_rate=fpr,
            avg_latency_s=stats.get("avg_latency_s", 0.0),
            total_cases_analyzed=len(valid_reports),
            # Evidence metrics would be calculated here
        )
        
        # 6. Save
        self.save_result(result, reports)
        
        return result
        
    def save_result(self, result: ExperimentResult, reports: List[DriftReport]):
        """Saves the experiment configuration, results, and detailed reports."""
        run_dir = self.storage_dir / result.experiment_id
        run_dir.mkdir(exist_ok=True)
        
        with open(run_dir / "result.json", "w") as f:
            f.write(result.to_json())
            
        with open(run_dir / "reports.jsonl", "w") as f:
            for r in reports:
                f.write(json.dumps(r.to_dict()) + "\n")
                
    def get_experiments(self) -> List[ExperimentResult]:
        """Loads all saved experiments."""
        results = []
        if self.storage_dir.exists():
            for d in self.storage_dir.iterdir():
                if d.is_dir():
                    res_file = d / "result.json"
                    if res_file.exists():
                        try:
                            with open(res_file, "r") as f:
                                data = json.load(f)
                                config_data = data.pop("config")
                                config = ExperimentConfig(**config_data)
                                results.append(ExperimentResult(config=config, **data))
                        except Exception as e:
                            logger.error(f"Failed to load experiment {d.name}: {e}")
        return sorted(results, key=lambda x: x.timestamp, reverse=True)

"""
DriftGuard Experiment Planner

Generates the complete experiment matrix from configured models, splits, and modes.
Does NOT execute inference. Produces a plan that can be inspected, validated, and 
then selectively executed.
"""
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from itertools import product
from pathlib import Path

from app.config import SUPPORTED_MODELS, SPLITS_DIR


@dataclass
class PlannedExperiment:
    """A single planned experiment configuration (no execution)."""
    model: str
    dataset_split: str
    rag_mode: str
    expected_cases: int
    expected_repositories: int
    rag_top_k: int = 5
    status: str = "PLANNED"  # PLANNED, RUNNING, COMPLETED, PARTIALLY_COMPLETED, FAILED, CANCELLED, MODEL_UNAVAILABLE
    evaluated_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    unavailable_cases: int = 0
    experiment_id: Optional[str] = None
    
    @property
    def remaining_cases(self) -> int:
        return max(0, self.expected_cases - self.evaluated_cases)


def get_split_counts() -> Dict[str, dict]:
    """Read actual dataset files and return exact case counts and repo counts per split."""
    counts = {}
    for split_name in ["train", "validation", "test"]:
        split_file = SPLITS_DIR / f"{split_name}.jsonl"
        case_count = 0
        repos = set()
        if split_file.exists():
            with open(split_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        case_count += 1
                        try:
                            c = json.loads(line)
                            repos.add(c.get("repository", ""))
                        except Exception:
                            pass
        counts[split_name.capitalize()] = {
            "cases": case_count,
            "repositories": len(repos),
        }
    return counts


def get_total_dataset_stats() -> dict:
    """Aggregate stats across all splits."""
    split_counts = get_split_counts()
    all_repos = set()
    total = 0
    for split_name in ["train", "validation", "test"]:
        split_file = SPLITS_DIR / f"{split_name}.jsonl"
        if split_file.exists():
            with open(split_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        total += 1
                        try:
                            c = json.loads(line)
                            all_repos.add(c.get("repository", ""))
                        except Exception:
                            pass
    return {
        "splits": split_counts,
        "total_cases": total,
        "unique_repositories": len(all_repos),
        "models": len(SUPPORTED_MODELS),
        "configured_models": SUPPORTED_MODELS,
    }


def generate_experiment_matrix(
    models: Optional[List[str]] = None,
    splits: Optional[List[str]] = None,
    rag_modes: Optional[List[str]] = None,
    rag_top_k: int = 5,
) -> List[PlannedExperiment]:
    """
    Generate the complete planned experiment matrix programmatically.
    
    Does NOT hardcode any counts — reads them from the actual dataset files.
    """
    if models is None:
        models = SUPPORTED_MODELS
    if splits is None:
        splits = ["Train", "Validation", "Test"]
    if rag_modes is None:
        rag_modes = ["Non-RAG", "RAG"]

    split_counts = get_split_counts()

    matrix = []
    for model, split, rag_mode in product(models, splits, rag_modes):
        sc = split_counts.get(split, {"cases": 0, "repositories": 0})
        matrix.append(PlannedExperiment(
            model=model,
            dataset_split=split,
            rag_mode=rag_mode,
            expected_cases=sc["cases"],
            expected_repositories=sc["repositories"],
            rag_top_k=rag_top_k if rag_mode != "Non-RAG" else 0,
        ))

    return matrix


def check_model_availability() -> Dict[str, bool]:
    """Check Ollama availability for every configured model."""
    from app.analysis.llm_client import LLMClient
    client = LLMClient()
    result = {}
    for m in SUPPORTED_MODELS:
        result[m] = client.check_model_available(m)
    return result


def reconcile_with_existing_runs(
    matrix: List[PlannedExperiment], 
    storage_dir: Path
) -> List[PlannedExperiment]:
    """
    Update status of planned experiments based on what already exists on disk.
    
    Matches by (model, split, rag_mode) and checks whether existing runs
    are smoke tests, partial, or complete.
    """
    from app.experiments.runner import ExperimentRunner
    runner = ExperimentRunner(storage_dir=storage_dir)
    existing = runner.get_experiments()

    # Index existing by (model, split, rag_mode) 
    # Multiple runs per config are possible; pick the best one
    best_runs = {}
    for e in existing:
        key = (e.config.model, e.config.dataset_split, e.config.rag_mode)
        is_smoke = getattr(e.config, "debug_sample_mode", False)
        prev = best_runs.get(key)
        
        if prev is None:
            best_runs[key] = e
        elif is_smoke and not getattr(prev.config, "debug_sample_mode", False):
            pass  # don't replace official with smoke
        elif e.total_cases_analyzed > prev.total_cases_analyzed:
            best_runs[key] = e

    for plan in matrix:
        key = (plan.model, plan.dataset_split, plan.rag_mode)
        run = best_runs.get(key)
        if run is None:
            plan.status = "PLANNED"
            continue

        is_smoke = getattr(run.config, "debug_sample_mode", False)
        plan.experiment_id = run.experiment_id
        plan.evaluated_cases = run.total_cases_analyzed
        plan.successful_cases = run.total_completed or 0
        plan.failed_cases = run.total_failed or 0
        plan.unavailable_cases = run.total_unavailable or 0

        if is_smoke:
            plan.status = "SMOKE_TEST_ONLY"
        elif "UNAVAILABLE" in run.status:
            plan.status = "MODEL_UNAVAILABLE"
        elif "FAILED" in run.status:
            plan.status = "FAILED"
        elif run.total_cases_analyzed >= plan.expected_cases:
            plan.status = "COMPLETED"
        elif run.total_cases_analyzed > 0:
            plan.status = "PARTIALLY_COMPLETED"
        else:
            plan.status = "PLANNED"

    return matrix


def matrix_summary(matrix: List[PlannedExperiment]) -> dict:
    """Summarize a matrix into aggregate stats."""
    total_planned = sum(p.expected_cases for p in matrix)
    total_evaluated = sum(p.evaluated_cases for p in matrix)
    status_counts = {}
    for p in matrix:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1
    
    models = sorted(set(p.model for p in matrix))
    splits = sorted(set(p.dataset_split for p in matrix))
    modes = sorted(set(p.rag_mode for p in matrix))
    
    return {
        "total_configurations": len(matrix),
        "planned_evaluations": total_planned,
        "evaluated_so_far": total_evaluated,
        "remaining": total_planned - total_evaluated,
        "models": models,
        "splits": splits,
        "modes": modes,
        "status_breakdown": status_counts,
    }

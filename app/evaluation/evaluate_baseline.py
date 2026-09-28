"""
DriftGuard Baseline Evaluation
Runs the baseline LLM (no RAG) on a sample of the test set and computes metrics.
"""

import json
import logging
import random
import time
from pathlib import Path
from typing import List, Optional
from collections import Counter

from app import config
from app.analysis.llm_client import LLMClient
from app.analysis.drift_detector import DriftDetector, DriftReport
from app.evaluation.metrics import (
    compute_detection_metrics,
    compute_classification_metrics,
    compute_severity_metrics,
    compute_evidence_quality,
    generate_summary_report,
)

logger = logging.getLogger(__name__)


def load_test_cases(split_file: Path = None, sample_size: int = None,
                    stratified: bool = True, seed: int = None) -> List[dict]:
    """
    Load test cases from JSONL, optionally with stratified sampling.

    Args:
        split_file: Path to test.jsonl (defaults to config)
        sample_size: Number of cases to sample (None = all)
        stratified: Whether to stratify by drift_type
        seed: Random seed for reproducibility

    Returns:
        List of case dicts
    """
    split_file = split_file or config.TEST_JSONL
    seed = seed or config.EVAL_RANDOM_SEED
    random.seed(seed)

    # Load all cases
    all_cases = []
    with open(split_file) as f:
        for line in f:
            all_cases.append(json.loads(line))

    logger.info(f"Loaded {len(all_cases)} cases from {split_file}")

    if sample_size is None or sample_size >= len(all_cases):
        return all_cases

    if stratified:
        return _stratified_sample(all_cases, sample_size, seed)
    else:
        random.shuffle(all_cases)
        return all_cases[:sample_size]


def _stratified_sample(cases: List[dict], sample_size: int, seed: int) -> List[dict]:
    """
    Stratified sampling ensuring all drift types are represented.
    Minority classes get at least min_per_class samples.
    """
    random.seed(seed)

    by_type = {}
    for c in cases:
        dt = c.get("drift_type", "unknown")
        by_type.setdefault(dt, []).append(c)

    # Ensure at least 3 samples per class (or all if fewer available)
    min_per_class = 3
    sampled = []
    remaining_budget = sample_size

    for dt, dt_cases in by_type.items():
        n_take = min(min_per_class, len(dt_cases))
        random.shuffle(dt_cases)
        sampled.extend(dt_cases[:n_take])
        remaining_budget -= n_take

    # Fill remaining budget proportionally
    if remaining_budget > 0:
        pool = []
        for dt, dt_cases in by_type.items():
            pool.extend(dt_cases[min_per_class:])  # Exclude already sampled
        random.shuffle(pool)
        sampled.extend(pool[:remaining_budget])

    random.shuffle(sampled)
    return sampled[:sample_size]


def run_baseline_evaluation(sample_size: int = None, model: str = None,
                            save_results: bool = True) -> dict:
    """
    Run the baseline (no RAG) evaluation.

    Args:
        sample_size: Number of test cases to evaluate (None = use config default)
        model: Override LLM model name
        save_results: Whether to save predictions and metrics to disk

    Returns:
        Dict with all metrics and predictions
    """
    sample_size = sample_size or config.EVAL_SAMPLE_SIZE
    config.ensure_dirs()

    print(f"\n{'='*60}")
    print(f"  DriftGuard Baseline Evaluation")
    print(f"  Model: {model or config.OLLAMA_MODEL}")
    print(f"  Sample size: {sample_size}")
    print(f"{'='*60}\n")

    # Load test cases
    print("[1/4] Loading test cases...")
    cases = load_test_cases(sample_size=sample_size, stratified=True)
    print(f"  Loaded {len(cases)} cases")

    # Distribution
    type_dist = Counter(c.get("drift_type", "?") for c in cases)
    print(f"  Distribution: {dict(type_dist)}")

    # Initialize detector
    print("\n[2/4] Initializing LLM...")
    llm = LLMClient(model=model)
    detector = DriftDetector(llm_client=llm)

    # Run predictions
    print(f"\n[3/4] Running baseline predictions on {len(cases)} cases...")
    start_time = time.time()

    def progress(current, total, report):
        if current % 5 == 0 or current == total:
            status = "✓" if report.parse_success else "✗"
            print(f"  [{current}/{total}] {status} {report.case_id} "
                  f"({report.latency_s:.1f}s)")

    reports = detector.analyze_cases(cases, mode="baseline", progress_callback=progress)
    total_time = time.time() - start_time

    print(f"\n  Completed in {total_time:.1f}s "
          f"(avg {total_time/len(cases):.1f}s/case)")

    # Compute metrics
    print("\n[4/4] Computing metrics...")
    results = _compute_all_metrics(cases, reports, llm.get_stats(), mode="baseline")

    # Save
    if save_results:
        _save_results(results, reports, cases, mode="baseline")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Detection F1:       {results['detection'].get('f1', 'N/A')}")
    print(f"  Classification Macro-F1: {results['classification'].get('macro_f1', 'N/A')}")
    print(f"  Parse Success Rate: {results['llm_stats'].get('parse_success_rate', 0):.1%}")
    print(f"  Avg Latency:        {results['llm_stats'].get('avg_latency_s', 0):.1f}s")

    return results


def _compute_all_metrics(cases: List[dict], reports: List[DriftReport],
                         llm_stats: dict, mode: str) -> dict:
    """Compute all evaluation metrics."""

    # Only evaluate cases where parsing succeeded
    valid_pairs = []
    for case, report in zip(cases, reports):
        if report.parse_success and report.prediction:
            valid_pairs.append((case, report))

    if not valid_pairs:
        logger.error("No valid predictions to evaluate!")
        return {"error": "No valid predictions", "llm_stats": llm_stats}

    parse_rate = len(valid_pairs) / len(cases)
    logger.info(f"Evaluating {len(valid_pairs)}/{len(cases)} cases "
                f"({parse_rate:.1%} parse rate)")

    gt_cases, pred_reports = zip(*valid_pairs)

    # Binary detection
    y_true_detect = [c.get("drift_present", True) for c in gt_cases]
    y_pred_detect = [r.prediction.drift_present for r in pred_reports]
    detection_metrics = compute_detection_metrics(y_true_detect, y_pred_detect)

    # Drift type classification
    y_true_type = [c.get("drift_type", "unknown") for c in gt_cases]
    y_pred_type = [r.prediction.drift_type for r in pred_reports]
    classification_metrics = compute_classification_metrics(y_true_type, y_pred_type)

    # Severity
    y_true_sev = [c.get("severity", "medium") for c in gt_cases]
    y_pred_sev = [r.prediction.severity for r in pred_reports]
    severity_metrics = compute_severity_metrics(y_true_sev, y_pred_sev)

    # Evidence quality
    pred_dicts = [
        {
            "evidence": r.prediction.evidence, 
            "verification_status": r.verification_status
        } 
        for r in pred_reports
    ]
    evidence_metrics = compute_evidence_quality(pred_dicts, list(gt_cases))

    # Generate markdown report
    report_md = generate_summary_report(
        detection_metrics, classification_metrics,
        severity_metrics, evidence_metrics,
        llm_stats, mode=mode,
    )

    return {
        "mode": mode,
        "detection": detection_metrics,
        "classification": classification_metrics,
        "severity": severity_metrics,
        "evidence": evidence_metrics,
        "llm_stats": llm_stats,
        "parse_rate": parse_rate,
        "total_cases": len(cases),
        "valid_cases": len(valid_pairs),
        "report_markdown": report_md,
    }


def _save_results(results: dict, reports: List[DriftReport],
                  cases: List[dict], mode: str):
    """Save predictions, metrics, and report to disk."""
    config.ensure_dirs()

    # Save predictions
    predictions_file = config.PREDICTIONS_DIR / f"{mode}_predictions.jsonl"
    with open(predictions_file, "w") as f:
        for report in reports:
            f.write(json.dumps(report.to_dict(), default=str) + "\n")
    print(f"  Saved predictions to {predictions_file}")

    # Save metrics
    metrics_file = config.METRICS_DIR / f"{mode}_metrics.json"
    # Remove non-serializable items
    save_results = {k: v for k, v in results.items() if k != "report_markdown"}
    with open(metrics_file, "w") as f:
        json.dump(save_results, f, indent=2, default=str)
    print(f"  Saved metrics to {metrics_file}")

    # Save markdown report
    report_file = config.REPORTS_DIR / f"{mode}_evaluation_report.md"
    with open(report_file, "w") as f:
        f.write(results.get("report_markdown", ""))
    print(f"  Saved report to {report_file}")

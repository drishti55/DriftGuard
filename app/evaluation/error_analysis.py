"""
DriftGuard Error Analysis
Analyzes prediction errors to identify patterns and areas for improvement.
"""

import json
import logging
from typing import List, Dict
from collections import Counter
from pathlib import Path

from app import config

logger = logging.getLogger(__name__)


def compare_baseline_vs_rag(baseline_results: dict, rag_results: dict) -> str:
    """
    Generate a comparison report between baseline and RAG evaluation results.

    Returns:
        Markdown-formatted comparison report
    """
    lines = [
        "# DriftGuard — Baseline vs RAG Comparison",
        "",
        "## Detection Metrics",
        "| Metric | Baseline | RAG | Δ |",
        "|--------|----------|-----|---|",
    ]

    for metric in ["accuracy", "precision", "recall", "f1",
                    "false_positive_rate", "false_negative_rate"]:
        b = baseline_results.get("detection", {}).get(metric, "N/A")
        r = rag_results.get("detection", {}).get(metric, "N/A")
        delta = ""
        if isinstance(b, (int, float)) and isinstance(r, (int, float)):
            d = r - b
            delta = f"+{d:.4f}" if d > 0 else f"{d:.4f}"
        lines.append(f"| {metric} | {b} | {r} | {delta} |")

    lines.extend([
        "",
        "## Classification Metrics",
        "| Metric | Baseline | RAG | Δ |",
        "|--------|----------|-----|---|",
    ])

    for metric in ["accuracy", "macro_f1"]:
        b = baseline_results.get("classification", {}).get(metric, "N/A")
        r = rag_results.get("classification", {}).get(metric, "N/A")
        delta = ""
        if isinstance(b, (int, float)) and isinstance(r, (int, float)):
            d = r - b
            delta = f"+{d:.4f}" if d > 0 else f"{d:.4f}"
        lines.append(f"| {metric} | {b} | {r} | {delta} |")

    lines.extend([
        "",
        "## Evidence Quality",
        "| Metric | Baseline | RAG | Δ |",
        "|--------|----------|-----|---|",
    ])

    for metric in ["mentions_artifacts_rate", "substantive_rate", "mentions_identifiers_rate"]:
        b = baseline_results.get("evidence", {}).get(metric, "N/A")
        r = rag_results.get("evidence", {}).get(metric, "N/A")
        delta = ""
        if isinstance(b, (int, float)) and isinstance(r, (int, float)):
            d = r - b
            delta = f"+{d:.4f}" if d > 0 else f"{d:.4f}"
        lines.append(f"| {metric} | {b} | {r} | {delta} |")

    lines.extend([
        "",
        "## Inference Stats",
        "| Metric | Baseline | RAG |",
        "|--------|----------|-----|",
        f"| Parse Success Rate | {baseline_results.get('llm_stats', {}).get('parse_success_rate', 'N/A')} | {rag_results.get('llm_stats', {}).get('parse_success_rate', 'N/A')} |",
        f"| Avg Latency (s) | {baseline_results.get('llm_stats', {}).get('avg_latency_s', 'N/A')} | {rag_results.get('llm_stats', {}).get('avg_latency_s', 'N/A')} |",
        f"| Total Cases | {baseline_results.get('total_cases', 'N/A')} | {rag_results.get('total_cases', 'N/A')} |",
        "",
    ])

    return "\n".join(lines)


def analyze_errors(predictions_file: Path, test_cases: List[dict] = None) -> dict:
    """
    Analyze prediction errors from a predictions JSONL file.

    Returns:
        Dict with error breakdowns by category
    """
    predictions = []
    with open(predictions_file) as f:
        for line in f:
            predictions.append(json.loads(line))

    # Load test cases if not provided
    if test_cases is None:
        test_cases = []
        with open(config.TEST_JSONL) as f:
            for line in f:
                test_cases.append(json.loads(line))

    # Build case lookup
    case_lookup = {c.get("case_id", ""): c for c in test_cases}

    errors = {
        "false_positives": [],
        "false_negatives": [],
        "wrong_type": [],
        "parse_failures": [],
    }
    error_by_type = Counter()
    error_by_language = Counter()

    for pred in predictions:
        case_id = pred.get("case_id", "")
        gt = case_lookup.get(case_id, {})

        if not pred.get("parse_success", False):
            errors["parse_failures"].append({
                "case_id": case_id,
                "error": pred.get("error", ""),
                "repository": pred.get("repository", ""),
            })
            continue

        pred_result = pred.get("prediction", {})
        if not pred_result:
            continue

        gt_present = gt.get("drift_present", True)
        pred_present = pred_result.get("drift_present", True)

        if pred_present and not gt_present:
            errors["false_positives"].append({
                "case_id": case_id,
                "repository": gt.get("repository", ""),
                "predicted_type": pred_result.get("drift_type", ""),
                "evidence": pred_result.get("evidence", "")[:200],
            })
            error_by_type["false_positive"] += 1
            error_by_language[gt.get("language", "?")] += 1

        elif not pred_present and gt_present:
            errors["false_negatives"].append({
                "case_id": case_id,
                "repository": gt.get("repository", ""),
                "actual_type": gt.get("drift_type", ""),
                "gt_evidence": gt.get("evidence", "")[:200],
            })
            error_by_type["false_negative"] += 1
            error_by_language[gt.get("language", "?")] += 1

        elif pred_present and gt_present:
            gt_type = gt.get("drift_type", "")
            pred_type = pred_result.get("drift_type", "")
            if gt_type != pred_type:
                errors["wrong_type"].append({
                    "case_id": case_id,
                    "repository": gt.get("repository", ""),
                    "actual_type": gt_type,
                    "predicted_type": pred_type,
                })
                error_by_type["wrong_type"] += 1

    return {
        "errors": errors,
        "error_by_type": dict(error_by_type),
        "error_by_language": dict(error_by_language),
        "total_predictions": len(predictions),
        "total_parse_failures": len(errors["parse_failures"]),
        "total_false_positives": len(errors["false_positives"]),
        "total_false_negatives": len(errors["false_negatives"]),
        "total_wrong_type": len(errors["wrong_type"]),
    }

"""
DriftGuard Evaluation Metrics
Computes classification metrics for drift detection and type classification.
"""

import json
import logging
from typing import List, Dict, Optional
from collections import Counter

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)

logger = logging.getLogger(__name__)


def compute_detection_metrics(y_true: List[bool], y_pred: List[bool]) -> dict:
    """
    Compute binary drift detection metrics.

    Args:
        y_true: Ground truth (True = drift present)
        y_pred: Predictions (True = drift present)

    Returns:
        Dict with accuracy, precision, recall, F1, FPR, FNR
    """
    if not y_true or not y_pred:
        return {"error": "Empty inputs"}

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    # False positive / negative rates
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[False, True]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "total": len(y_true),
    }


def compute_classification_metrics(y_true: List[str], y_pred: List[str],
                                   labels: List[str] = None) -> dict:
    """
    Compute drift type classification metrics.

    Args:
        y_true: Ground truth drift types
        y_pred: Predicted drift types
        labels: Optional list of all possible labels

    Returns:
        Dict with accuracy, macro-F1, per-class metrics, confusion matrix
    """
    if not y_true or not y_pred:
        return {"error": "Empty inputs"}

    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))

    accuracy = accuracy_score(y_true, y_pred)

    # Macro-F1
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)

    # Per-class report
    report = classification_report(
        y_true, y_pred, labels=labels,
        output_dict=True, zero_division=0
    )

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Per-class metrics
    per_class = {}
    for label in labels:
        if label in report:
            per_class[label] = {
                "precision": round(report[label]["precision"], 4),
                "recall": round(report[label]["recall"], 4),
                "f1": round(report[label]["f1-score"], 4),
                "support": int(report[label]["support"]),
            }

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
        "total": len(y_true),
    }


def compute_severity_metrics(y_true: List[str], y_pred: List[str]) -> dict:
    """Compute severity prediction metrics."""
    labels = ["none", "low", "medium", "high"]
    return compute_classification_metrics(y_true, y_pred, labels=labels)


def compute_evidence_quality(predictions: List[dict], ground_truth: List[dict]) -> dict:
    """
    Compute evidence quality metrics (heuristic-based).

    Checks:
    - Does the evidence mention the correct artifact paths?
    - Is the evidence non-empty and substantive?
    - Does the evidence mention specific identifiers (function names, module names)?
    """
    if not predictions:
        return {"error": "No predictions"}

    scores = {
        "mentions_artifacts": 0,
        "is_substantive": 0,
        "mentions_identifiers": 0,
        "verified_evidence": 0,
        "total_evaluated": 0,
    }

    for pred, gt in zip(predictions, ground_truth):
        pred_evidence = pred.get("evidence", "")
        verification_status = pred.get("verification_status", "No Drift")
        gt_a1_path = gt.get("artifact_1", {}).get("path", "")
        gt_a2_path = gt.get("artifact_2", {}).get("path", "")

        if not pred_evidence:
            scores["total_evaluated"] += 1
            continue

        scores["total_evaluated"] += 1

        # Check if evidence mentions artifact paths or filenames
        a1_name = gt_a1_path.split("/")[-1] if gt_a1_path else ""
        a2_name = gt_a2_path.split("/")[-1] if gt_a2_path else ""
        if (a1_name and a1_name in pred_evidence) or (a2_name and a2_name in pred_evidence):
            scores["mentions_artifacts"] += 1

        # Check substantiveness (more than 20 chars)
        if len(pred_evidence.strip()) > 20:
            scores["is_substantive"] += 1

        if verification_status == "Confirmed Drift":
            scores["verified_evidence"] += 1

        # Check for specific identifiers (backtick-quoted names, function names)
        import re
        identifiers = re.findall(r'`([^`]+)`', pred_evidence)
        if identifiers or re.search(r'\b\w+\(\)', pred_evidence):
            scores["mentions_identifiers"] += 1

    total = scores["total_evaluated"]
    if total > 0:
        return {
            "mentions_artifacts_rate": round(scores["mentions_artifacts"] / total, 4),
            "substantive_rate": round(scores["is_substantive"] / total, 4),
            "mentions_identifiers_rate": round(scores["mentions_identifiers"] / total, 4),
            "verification_rate": round(scores["verified_evidence"] / total, 4),
            "total_evaluated": total,
        }

    return scores


def generate_summary_report(detection_metrics: dict, classification_metrics: dict,
                            severity_metrics: dict, evidence_metrics: dict,
                            llm_stats: dict, mode: str = "baseline") -> str:
    """Generate a human-readable summary report."""
    lines = [
        f"# DriftGuard Evaluation Report — {mode.upper()} Mode",
        f"",
        f"## Drift Detection (Binary)",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {detection_metrics.get('accuracy', 'N/A')} |",
        f"| Precision | {detection_metrics.get('precision', 'N/A')} |",
        f"| Recall | {detection_metrics.get('recall', 'N/A')} |",
        f"| F1-Score | {detection_metrics.get('f1', 'N/A')} |",
        f"| False Positive Rate | {detection_metrics.get('false_positive_rate', 'N/A')} |",
        f"| False Negative Rate | {detection_metrics.get('false_negative_rate', 'N/A')} |",
        f"| Total Cases | {detection_metrics.get('total', 'N/A')} |",
        f"",
        f"## Drift Classification",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {classification_metrics.get('accuracy', 'N/A')} |",
        f"| Macro-F1 | {classification_metrics.get('macro_f1', 'N/A')} |",
        f"",
    ]

    # Per-class table
    per_class = classification_metrics.get("per_class", {})
    if per_class:
        lines.append("### Per-Class Metrics")
        lines.append("| Drift Type | Precision | Recall | F1 | Support |")
        lines.append("|-----------|-----------|--------|-----|---------|")
        for label, metrics in sorted(per_class.items()):
            lines.append(
                f"| {label} | {metrics['precision']} | {metrics['recall']} "
                f"| {metrics['f1']} | {metrics['support']} |"
            )
        lines.append("")

    # Severity
    lines.extend([
        f"## Severity Prediction",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {severity_metrics.get('accuracy', 'N/A')} |",
        f"| Macro-F1 | {severity_metrics.get('macro_f1', 'N/A')} |",
        f"",
    ])

    # Evidence quality
    lines.extend([
        f"## Evidence Quality",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Mentions Artifacts | {evidence_metrics.get('mentions_artifacts_rate', 'N/A')} |",
        f"| Substantive | {evidence_metrics.get('substantive_rate', 'N/A')} |",
        f"| Mentions Identifiers | {evidence_metrics.get('mentions_identifiers_rate', 'N/A')} |",
        f"| Verified Citation Rate | {evidence_metrics.get('verification_rate', 'N/A')} |",
        f"",
    ])

    # LLM stats
    if llm_stats:
        lines.extend([
            f"## LLM Inference Stats",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Calls | {llm_stats.get('total_calls', 'N/A')} |",
            f"| Parse Success Rate | {llm_stats.get('parse_success_rate', 'N/A'):.1%}" if isinstance(llm_stats.get('parse_success_rate'), float) else f"| Parse Success Rate | {llm_stats.get('parse_success_rate', 'N/A')} |",
            f"| Avg Latency | {llm_stats.get('avg_latency_s', 'N/A'):.1f}s" if isinstance(llm_stats.get('avg_latency_s'), float) else f"| Avg Latency | {llm_stats.get('avg_latency_s', 'N/A')} |",
            f"| Fallbacks Used | {llm_stats.get('fallback_used', 'N/A')} |",
            f"",
        ])

    return "\n".join(lines)

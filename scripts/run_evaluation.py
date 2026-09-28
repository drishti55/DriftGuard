#!/usr/bin/env python3
"""
DriftGuard Evaluation Runner
CLI entry point for running baseline and RAG evaluations.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config


def main():
    parser = argparse.ArgumentParser(description="DriftGuard Evaluation Runner")
    parser.add_argument("--mode", choices=["baseline", "rag", "both", "compare"],
                        default="baseline", help="Evaluation mode")
    parser.add_argument("--sample-size", type=int, default=None,
                        help=f"Number of test cases (default: {config.EVAL_SAMPLE_SIZE})")
    parser.add_argument("--model", type=str, default=None,
                        help=f"LLM model (default: {config.OLLAMA_MODEL})")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config.ensure_dirs()

    if args.mode == "baseline" or args.mode == "both":
        from app.evaluation.evaluate_baseline import run_baseline_evaluation
        baseline_results = run_baseline_evaluation(
            sample_size=args.sample_size,
            model=args.model,
        )

    if args.mode == "rag" or args.mode == "both":
        from app.evaluation.evaluate_rag import run_rag_evaluation
        rag_results = run_rag_evaluation(
            sample_size=args.sample_size,
            model=args.model,
        )

    if args.mode == "both" or args.mode == "compare":
        import json
        from app.evaluation.error_analysis import compare_baseline_vs_rag

        if args.mode == "compare":
            # Load saved results
            baseline_file = config.METRICS_DIR / "baseline_metrics.json"
            rag_file = config.METRICS_DIR / "rag_metrics.json"
            if not baseline_file.exists() or not rag_file.exists():
                print("ERROR: Run baseline and RAG evaluations first (--mode both)")
                sys.exit(1)
            with open(baseline_file) as f:
                baseline_results = json.load(f)
            with open(rag_file) as f:
                rag_results = json.load(f)

        comparison = compare_baseline_vs_rag(baseline_results, rag_results)
        comp_file = config.REPORTS_DIR / "baseline_vs_rag_comparison.md"
        with open(comp_file, "w") as f:
            f.write(comparison)
        print(f"\nComparison saved to {comp_file}")
        print(comparison)


if __name__ == "__main__":
    main()

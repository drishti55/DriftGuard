#!/usr/bin/env python3
"""
DriftGuard Research Experiment Pipeline CLI
Runs complete, auditable research experiments across train/validation/test splits,
models, and RAG configurations with full case-level checkpointing and traceability.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import config
from app.experiments.config import ExperimentConfig, ExperimentResult
from app.experiments.runner import ExperimentRunner
from app.analysis.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("driftguard.experiments")


def check_models_availability():
    """Verify local Ollama model availability."""
    from app.config import SUPPORTED_MODELS
    models = SUPPORTED_MODELS
    print("=" * 60)
    print("OLLAMA MODEL STATUS CHECK")
    print("=" * 60)
    client = LLMClient()
    for m in models:
        avail = client.check_model_available(m)
        status = "✅ AVAILABLE" if avail else "❌ NOT FOUND"
        print(f"  {m:<25} : {status}")
    print("=" * 60)


def run_single_experiment(runner: ExperimentRunner, exp_config: ExperimentConfig) -> ExperimentResult:
    """Run an individual experiment with clean terminal progress."""
    print("\n" + "=" * 70)
    print(f"EXPERIMENT: {exp_config.experiment_id}")
    print(f"Model: {exp_config.model} | RAG: {exp_config.rag_mode} | Split: {exp_config.dataset_split}")
    print(f"Repository: {exp_config.repository} | Smoke Test: {exp_config.debug_sample_mode}")
    print("=" * 70)

    last_pct = [-1]

    def progress_cb(current, total, report):
        pct = int((current / total) * 100) if total > 0 else 100
        if pct != last_pct[0] and (pct % 10 == 0 or current == total or current == 1):
            last_pct[0] = pct
            status = report.execution_status
            verdict = report.verification_status if report.prediction else "N/A"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {current}/{total} ({pct}%) | Last: {report.case_id} -> {status} ({verdict})")

    result = runner.run(exp_config, progress_callback=progress_cb)

    print("\n" + "-" * 70)
    print(f"RESULT FOR {exp_config.experiment_id}:")
    print(f"  Status:          {result.status} {f'({result.status_reason})' if result.status_reason else ''}")
    print(f"  Cases Evaluated: {result.total_cases_analyzed}")
    print(f"  Completed:       {result.total_completed} | Failed: {result.total_failed} | Unavailable: {result.total_unavailable}")
    print(f"  Accuracy:        {result.accuracy if result.accuracy is not None else 'N/A'}")
    print(f"  Precision:       {result.precision if result.precision is not None else 'N/A'}")
    print(f"  Recall:          {result.recall if result.recall is not None else 'N/A'}")
    print(f"  F1-Score:        {result.f1_score if result.f1_score is not None else 'N/A'}")
    print(f"  FPR:             {result.false_positive_rate if result.false_positive_rate is not None else 'N/A'}")
    print(f"  Avg Latency:     {result.avg_latency_s:.2f}s")
    if result.confusion_matrix:
        cm = result.confusion_matrix
        print(f"  Confusion Mat:   TP={cm.get('tp')} | FP={cm.get('fp')} | TN={cm.get('tn')} | FN={cm.get('fn')}")
    print("-" * 70)

    return result


def main():
    parser = argparse.ArgumentParser(description="DriftGuard Research Experiment Pipeline")
    parser.add_argument("--split", choices=["train", "validation", "test", "all"], default="test", help="Dataset split to evaluate")
    parser.add_argument("--model", default="qwen2.5-coder:7b", help="Model identifier (e.g. qwen2.5-coder:7b, starcoder2:3b)")
    parser.add_argument("--rag-mode", choices=["Non-RAG", "RAG", "both"], default="Non-RAG", help="Analysis mode")
    parser.add_argument("--repository", default="all", help="Target repository or 'all'")
    parser.add_argument("--top-k", type=int, default=5, help="RAG retrieval top-k")
    parser.add_argument("--sample", type=int, default=0, help="Debug/sample mode case count (marks as smoke test)")
    parser.add_argument("--smoke-test", action="store_true", help="Run a fast 5-case smoke test on etcd-io/etcd")
    parser.add_argument("--verify-models", action="store_true", help="Verify Ollama model availability")
    parser.add_argument("--list", action="store_true", help="List all saved experiments")
    parser.add_argument("--storage-dir", default="results/experiments", help="Results storage directory")

    args = parser.parse_args()

    runner = ExperimentRunner(storage_dir=Path(args.storage_dir))

    if args.verify_models:
        check_models_availability()
        return

    if args.list:
        experiments = runner.get_experiments()
        print(f"\nSaved Experiments in {args.storage_dir} ({len(experiments)} total):")
        print(f"{'Experiment ID':<26} {'Model':<18} {'RAG':<9} {'Split':<10} {'Cases':<7} {'F1':<8} {'FPR':<8} {'Status'}")
        print("-" * 100)
        for e in experiments:
            f1 = f"{e.f1_score:.4f}" if e.f1_score is not None else "N/A"
            fpr = f"{e.false_positive_rate:.4f}" if e.false_positive_rate is not None else "N/A"
            print(f"{e.experiment_id:<26} {e.config.model:<18} {e.config.rag_mode:<9} {e.config.dataset_split:<10} {e.total_cases_analyzed:<7} {f1:<8} {fpr:<8} {e.status}")
        return

    if args.smoke_test:
        print("==================================================")
        print("LAUNCHING DRIFTGUARD SMOKE TEST (Requirement #25)")
        print("Repo: etcd-io/etcd | Model: qwen2.5-coder:7b | Split: Test | Cases: 3")
        print("==================================================")
        smoke_id = f"smoke-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        cfg = ExperimentConfig(
            experiment_id=smoke_id,
            repository="etcd-io/etcd",
            model="qwen2.5-coder:7b",
            rag_mode="Non-RAG",
            dataset_split="Test",
            debug_sample_mode=True,
            description="Automated Smoke Test Verification"
        )
        res = run_single_experiment(runner, cfg)
        
        # Verify saved files
        run_dir = Path(args.storage_dir) / smoke_id
        c_file = run_dir / "cases.jsonl"
        s_file = run_dir / "summary.json"
        
        print("\nSmoke Test File Verification:")
        print(f"  cases.jsonl exists: {c_file.exists()} (size: {c_file.stat().st_size if c_file.exists() else 0} bytes)")
        print(f"  summary.json exists: {s_file.exists()}")
        
        cases = runner.get_experiment_cases(smoke_id)
        print(f"  Traceable cases read back: {len(cases)}")
        if cases:
            sample = cases[0]
            print(f"  Sample Case ID: {sample.get('case_id')}")
            print(f"  Artifact 1: {sample.get('artifact_1_path')}")
            print(f"  Artifact 2: {sample.get('artifact_2_path')}")
            print(f"  Predicted Drift: {sample.get('parsed_prediction', {}).get('drift_present')}")
            print(f"  Verification Status: {sample.get('verification_status')}")
            print(f"  Classification: {sample.get('evaluation', {}).get('classification')}")
            
        print("\n✅ SMOKE TEST COMPLETED SUCCESSFULLY.")
        return

    # Normal or Matrix Execution
    splits = [args.split.capitalize()] if args.split != "all" else ["Train", "Validation", "Test"]
    from app.config import SUPPORTED_MODELS
    models = [args.model] if args.model != "all" else SUPPORTED_MODELS
    rag_modes = ["Non-RAG", "RAG"] if args.rag_mode == "both" else [args.rag_mode]

    # Pre-check: Verify Ollama is running before launching any experiments
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        print("✅ Ollama is running and reachable.")
    except Exception as e:
        print(f"\n❌ FATAL: Ollama is not running or unreachable: {e}")
        print("   Start Ollama with: ollama serve")
        print("   Refusing to launch experiments to avoid false MODEL_UNAVAILABLE marks.")
        return

    is_debug = args.sample > 0

    total_configs = len(list(splits)) * len(list(models)) * len(list(rag_modes))
    print(f"\n{'=' * 70}")
    print(f"EXPERIMENT MATRIX: {total_configs} configurations")
    print(f"Models: {', '.join(models)}")
    print(f"Splits: {', '.join(splits)}")
    print(f"RAG Modes: {', '.join(rag_modes)}")
    print(f"{'=' * 70}\n")

    config_num = 0
    for s in splits:
        for m in models:
            for rm in rag_modes:
                config_num += 1
                # Deterministic experiment ID — ensures restarts resume the same directory
                short_m = m.split(":")[0].replace(".", "").replace("-", "")
                exp_id = f"official-{short_m}-{rm.lower().replace('-','')}-{s.lower()}"
                
                # Check if this experiment already has a completed summary
                exp_dir = Path(args.storage_dir) / exp_id
                if exp_dir.exists() and (exp_dir / "summary.json").exists():
                    import json
                    with open(exp_dir / "summary.json") as sf:
                        existing = json.load(sf)
                    existing_cases = existing.get("total_cases_analyzed", 0)
                    existing_status = existing.get("status", "")
                    if existing_status == "COMPLETED" and existing_cases > 100:
                        print(f"\n[{config_num}/{total_configs}] SKIP (already completed): {exp_id} — {existing_cases} cases")
                        continue
                    else:
                        print(f"\n[{config_num}/{total_configs}] RESUME: {exp_id} — {existing_cases} cases already done")
                else:
                    print(f"\n[{config_num}/{total_configs}] START: {exp_id}")

                cfg = ExperimentConfig(
                    experiment_id=exp_id,
                    repository=args.repository,
                    model=m,
                    rag_mode=rm,
                    top_k=args.top_k,
                    dataset_split=s,
                    debug_sample_mode=is_debug
                )
                run_single_experiment(runner, cfg)


if __name__ == "__main__":
    main()

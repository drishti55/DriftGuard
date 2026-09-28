"""
DriftGuard RAG Evaluation
Runs the RAG-enhanced LLM on a sample of the test set and computes metrics.
"""

import json
import logging
import time
from typing import List, Optional
from collections import Counter

from app import config
from app.analysis.llm_client import LLMClient
from app.analysis.drift_detector import DriftDetector
from app.retrieval.vector_store import VectorStore
from app.retrieval.retriever import Retriever
from app.ingestion.repository_loader import RepositoryLoader
from app.evaluation.evaluate_baseline import (
    load_test_cases, _compute_all_metrics, _save_results,
)

logger = logging.getLogger(__name__)


def build_index_for_test_repos(cases: List[dict], retriever: Retriever):
    """
    Build vector index for all repositories referenced in the test cases.
    """
    repos = set(c.get("repository", "") for c in cases)
    print(f"  Building index for {len(repos)} repositories...")

    for i, repo in enumerate(sorted(repos)):
        try:
            retriever.build_index_for_repo(repo, use_metadata=True)
        except Exception as e:
            logger.warning(f"  Failed to index {repo}: {e}")

        if (i + 1) % 10 == 0:
            print(f"  Indexed {i + 1}/{len(repos)} repos")

    stats = retriever.vector_store.get_collection_stats()
    print(f"  Index built: {stats['total_chunks']} total chunks")


def run_rag_evaluation(sample_size: int = None, model: str = None,
                       save_results: bool = True) -> dict:
    """
    Run the RAG-enhanced evaluation.

    Args:
        sample_size: Number of test cases to evaluate
        model: Override LLM model name
        save_results: Whether to save results to disk

    Returns:
        Dict with all metrics
    """
    sample_size = sample_size or config.EVAL_SAMPLE_SIZE
    config.ensure_dirs()

    print(f"\n{'='*60}")
    print(f"  DriftGuard RAG Evaluation")
    print(f"  Model: {model or config.OLLAMA_MODEL}")
    print(f"  Sample size: {sample_size}")
    print(f"{'='*60}\n")

    # Load test cases
    print("[1/5] Loading test cases...")
    cases = load_test_cases(sample_size=sample_size, stratified=True)
    print(f"  Loaded {len(cases)} cases")

    type_dist = Counter(c.get("drift_type", "?") for c in cases)
    print(f"  Distribution: {dict(type_dist)}")

    # Initialize RAG components
    print("\n[2/5] Initializing RAG pipeline...")
    repo_loader = RepositoryLoader()
    vector_store = VectorStore()
    retriever = Retriever(vector_store=vector_store, repo_loader=repo_loader)

    # Build index
    print("\n[3/5] Building vector index for test repositories...")
    index_start = time.time()
    build_index_for_test_repos(cases, retriever)
    index_time = time.time() - index_start
    print(f"  Index built in {index_time:.1f}s")

    # Initialize detector with RAG
    print("\n[4/5] Running RAG predictions...")
    llm = LLMClient(model=model)
    detector = DriftDetector(llm_client=llm, retriever=retriever)

    start_time = time.time()

    def progress(current, total, report):
        if current % 5 == 0 or current == total:
            status = "✓" if report.parse_success else "✗"
            print(f"  [{current}/{total}] {status} {report.case_id} "
                  f"({report.latency_s:.1f}s)")

    reports = detector.analyze_cases(cases, mode="rag", progress_callback=progress)
    total_time = time.time() - start_time

    print(f"\n  Completed in {total_time:.1f}s "
          f"(avg {total_time/len(cases):.1f}s/case)")

    # Compute metrics
    print("\n[5/5] Computing metrics...")
    llm_stats = llm.get_stats()
    llm_stats["index_build_time_s"] = index_time
    results = _compute_all_metrics(cases, reports, llm_stats, mode="rag")

    if save_results:
        _save_results(results, reports, cases, mode="rag")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RAG RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Detection F1:       {results['detection'].get('f1', 'N/A')}")
    print(f"  Classification Macro-F1: {results['classification'].get('macro_f1', 'N/A')}")
    print(f"  Parse Success Rate: {results['llm_stats'].get('parse_success_rate', 0):.1%}")
    print(f"  Avg Latency:        {results['llm_stats'].get('avg_latency_s', 0):.1f}s")
    print(f"  Index Build Time:   {index_time:.1f}s")

    return results

#!/usr/bin/env python3
"""
DriftGuard Analysis Runner
CLI entry point for analyzing a repository from the local dataset.
Uses RelationshipGraph for fact-based cross-artifact candidate discovery.
"""

import sys
import json
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config
from app.analysis.llm_client import LLMClient
from app.analysis.drift_pipeline import DriftPipeline
from app.ingestion.repository_loader import RepositoryLoader
from app.ingestion.repository_ingestor import IngestedRepository
from app.ingestion.repository_scanner import RepositoryScanner
from app.analysis.relationship_graph import RelationshipGraph
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description="DriftGuard Repository Analyzer")
    parser.add_argument("repository", type=str, nargs="?",
                        help="Repository name (e.g., 'OT-CONTAINER-KIT/redis-operator')")
    parser.add_argument("--list", action="store_true", help="List available repositories")
    parser.add_argument("--max-candidates", type=int, default=None,
                        help="Max candidates to analyze (default: all)")
    parser.add_argument("--model", type=str, default=None,
                        help=f"LLM model (default: {config.OLLAMA_MODEL})")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file for JSON results")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    loader = RepositoryLoader()

    if args.list:
        repos = loader.list_available_repos()
        print(f"\nAvailable repositories ({len(repos)}):\n")
        for r in repos:
            print(f"  {r}")
        return

    if not args.repository:
        parser.print_help()
        print("\nUse --list to see available repositories.")
        return

    repo_name = args.repository
    info = loader.get_repo_info(repo_name)
    if not info:
        # Check if it's a directory name with underscore
        alt_name = repo_name.replace("/", "_")
        local_dir = config.REPOS_DIR / alt_name
        if local_dir.exists():
            pass
        else:
            print(f"ERROR: Repository '{repo_name}' not found.")
            sys.exit(1)

    repo_dir_name = repo_name.replace("/", "_")
    target_dir = (info.snapshot_path if info and info.snapshot_path else None) or (config.REPOS_DIR / repo_dir_name)

    print(f"\n{'='*60}")
    print(f"  DriftGuard Comprehensive Repository Analysis")
    print(f"  Repository: {repo_name}")
    print(f"  Path: {target_dir}")
    print(f"{'='*60}\n")

    # Ingest and scan workspace
    print("[1/3] Scanning repository inventory...")
    ingested = IngestedRepository(
        source_type="local",
        workspace_path=target_dir,
        original_source=repo_name,
        commit_sha=info.commit_sha if info else ""
    )
    scanner = RepositoryScanner()
    scanned_info = scanner.scan(ingested)

    metrics = scanned_info.scan_metrics
    print(f"  Files discovered: {metrics['files_discovered']}")
    print(f"  Relevant artifacts: {metrics['relevant_artifacts']}")
    print(f"  Ignored vendor/theme/cache: {metrics['ignored_vendor_cache']}")
    print(f"  Ignored binaries: {metrics['ignored_binary']}")
    print(f"  Detected language: {scanned_info.language}")
    print(f"  Detected framework: {scanned_info.framework}")
    print(f"  Cross-artifact relationships: {metrics['relationships_discovered']}")
    print(f"  Drift candidates generated: {metrics['candidates_generated']}")

    # Run analysis
    candidates_to_run = scanned_info.drift_candidates
    if args.max_candidates:
        candidates_to_run = candidates_to_run[:args.max_candidates]

    print(f"\n[2/3] Analyzing {len(candidates_to_run)} candidate relationships (model: {args.model or config.OLLAMA_MODEL})...")
    llm = LLMClient(model=args.model)
    pipeline = DriftPipeline(workspace_path=target_dir, llm_client=llm)

    result = pipeline.analyze_repository(
        repo_info=scanned_info,
        max_candidates=args.max_candidates,
        progress_callback=lambda cur, tot, msg: print(f"  [{cur}/{tot}] {msg}") if cur % 10 == 0 or cur == tot else None
    )

    # Summary
    print(f"\n[3/3] Results:")
    res_metrics = result["metrics"]
    print(f"  Status: {result['status']}")
    print(f"  Candidates generated: {res_metrics['candidates_generated']}")
    print(f"  Candidates analyzed: {res_metrics['candidates_analyzed']}")
    print(f"  Candidates verified: {res_metrics['candidates_verified']}")
    print(f"  Confirmed drifts: {res_metrics['drifts_found']}")

    confirmed = result["confirmed_drifts"]
    if confirmed:
        print(f"\n  Confirmed Drifts:")
        for r in confirmed:
            p = r.prediction
            type_label = p.drift_type.replace('_', ' ').title() if p else "Cross-Artifact"
            print(f"    • [{type_label}] {r.artifact_1_path} ↔ {r.artifact_2_path}")
            if p and p.evidence:
                print(f"      Contradiction: {p.evidence}")
    elif result["status"] == "NO DRIFT FOUND":
        print(f"\n  ✅ NO DRIFT FOUND: Repository is consistent across all {res_metrics['candidates_analyzed']} analyzed candidates.")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump({
                "metrics": res_metrics,
                "status": result["status"],
                "drifts": [r.to_dict() for r in confirmed]
            }, f, indent=2)
        print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()

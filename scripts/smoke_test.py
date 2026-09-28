#!/usr/bin/env python3
"""
DriftGuard Smoke Test
Runs 3 test cases through the baseline LLM to verify the full pipeline works.
"""

import sys
import json
import time
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app import config
from app.analysis.llm_client import LLMClient
from app.analysis.drift_detector import DriftDetector

def main():
    print("=" * 60)
    print("  DriftGuard Smoke Test")
    print("=" * 60)

    # 1. Verify config paths
    print("\n[1/5] Checking config paths...")
    paths = {
        "DATASET_DIR": config.DATASET_DIR,
        "REPOS_DIR": config.REPOS_DIR,
        "TEST_JSONL": config.TEST_JSONL,
        "CLONE_RESULTS_JSON": config.CLONE_RESULTS_JSON,
    }
    for name, path in paths.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")
        if not exists:
            print(f"     ERROR: Path does not exist!")
            if name == "TEST_JSONL":
                sys.exit(1)

    # 2. Load 3 test cases (one per drift type if possible)
    print("\n[2/5] Loading test cases...")
    cases = []
    seen_types = set()
    with open(config.TEST_JSONL) as f:
        for line in f:
            c = json.loads(line)
            dt = c.get("drift_type", "")
            if dt not in seen_types and len(cases) < 3:
                cases.append(c)
                seen_types.add(dt)
            if len(cases) >= 3:
                break

    for c in cases:
        print(f"  Case {c['case_id']}: {c['drift_type']} | {c['repository']} | "
              f"{c['artifact_1']['path']} ↔ {c['artifact_2']['path']}")

    # 3. Check Ollama
    print(f"\n[3/5] Checking Ollama ({config.OLLAMA_MODEL})...")
    llm = LLMClient()
    available = llm.check_model_available(config.OLLAMA_MODEL)
    print(f"  Model available: {'✅' if available else '❌'}")
    if not available:
        print(f"  ERROR: Model {config.OLLAMA_MODEL} not found in Ollama!")
        print(f"  Run: ollama pull {config.OLLAMA_MODEL}")
        sys.exit(1)

    # 4. Run predictions
    print(f"\n[4/5] Running predictions on {len(cases)} cases...")
    detector = DriftDetector(llm_client=llm)

    results = []
    for i, case in enumerate(cases):
        print(f"\n  --- Case {i+1}/{len(cases)}: {case['case_id']} ---")
        print(f"  Type: {case['drift_type']} | Repo: {case['repository']}")

        start = time.time()
        report = detector.analyze_case(case, mode="baseline")
        elapsed = time.time() - start

        results.append(report)

        if report.parse_success and report.prediction:
            p = report.prediction
            print(f"  ✅ Parse succeeded ({elapsed:.1f}s)")
            print(f"     drift_present: {p.drift_present}")
            print(f"     drift_type:    {p.drift_type}")
            print(f"     severity:      {p.severity}")
            print(f"     evidence:      {p.evidence[:150]}")
            print(f"     expected_fix:  {p.expected_fix[:150]}")

            # Compare with ground truth
            gt_type = case.get("drift_type", "")
            gt_present = case.get("drift_present", True)
            match_present = (p.drift_present == gt_present)
            match_type = (p.drift_type == gt_type)
            print(f"     GT match: present={'✅' if match_present else '❌'} "
                  f"type={'✅' if match_type else '❌'}")
        else:
            print(f"  ❌ Parse FAILED ({elapsed:.1f}s)")
            print(f"     Error: {report.error}")
            print(f"     Raw output: {report.raw_output[:200]}")

    # 5. Summary
    print(f"\n{'='*60}")
    print(f"  SMOKE TEST SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for r in results if r.parse_success)
    stats = llm.get_stats()
    print(f"  Cases tested:     {len(results)}")
    print(f"  Parse successes:  {success}/{len(results)}")
    print(f"  Avg latency:      {stats['avg_latency_s']:.1f}s")
    print(f"  Total tokens:     {stats['total_tokens']}")

    if success == len(results):
        print(f"\n  ✅ SMOKE TEST PASSED — Pipeline is working!")
    elif success > 0:
        print(f"\n  ⚠️  PARTIAL PASS — {success}/{len(results)} cases parsed")
    else:
        print(f"\n  ❌ SMOKE TEST FAILED — No cases parsed successfully")

    return success > 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)

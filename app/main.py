#!/usr/bin/env python3
"""
DriftGuard Unified CLI Entry Point
AIDevOps tool for repository delta perception, stack detection, and consistency audits.
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config_schema import DriftGuardConfig
from app.agents.delta_scanner import GitDeltaScanner
from app.agents.stack_detector import StackDetector
from app.agents.coordinator import CoordinatorAgent


def main():
    parser = argparse.ArgumentParser(
        description="🛡️ DriftGuard — Autonomous AIDevOps Inconsistency Detection & Self-Healing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app/main.py perceive --base HEAD~1
  python app/main.py scan-stack
  python app/main.py diff --base main
  python app/main.py config --show
  python app/main.py ui
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # 1. Perceive Command (Phase 1 Coordinator Pipeline)
    perceive_parser = subparsers.add_parser("perceive", help="Scan git delta and detect technology stack")
    perceive_parser.add_argument("--workspace", type=str, default=".", help="Target workspace path (default: current dir)")
    perceive_parser.add_argument("--branch", type=str, default=None, help="Target branch name")
    perceive_parser.add_argument("--base", type=str, default=None, help="Base branch/commit to compare against")
    perceive_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # 2. Scan-Stack Command
    stack_parser = subparsers.add_parser("scan-stack", help="Autonomously detect frameworks and build/test commands")
    stack_parser.add_argument("--workspace", type=str, default=".", help="Target workspace path")
    stack_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # 3. Diff Command
    diff_parser = subparsers.add_parser("diff", help="Inspect git delta and modified line hunks")
    diff_parser.add_argument("--workspace", type=str, default=".", help="Target workspace path")
    diff_parser.add_argument("--base", type=str, default=None, help="Base branch/commit to compare against")
    diff_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # 4. Config Command
    config_parser = subparsers.add_parser("config", help="Inspect and validate .driftguard.yml configuration")
    config_parser.add_argument("--path", type=str, default=None, help="Path to .driftguard.yml")
    config_parser.add_argument("--show", action="store_true", help="Print loaded configuration YAML")

    # 5. UI Command
    subparsers.add_parser("ui", help="Launch Streamlit management interface")

    # 6. Legacy Analyze (maintained for dataset backwards-compatibility)
    analyze_parser = subparsers.add_parser("analyze", help="Analyze repository for drift")
    analyze_parser.add_argument("repository", nargs="?", default=".", help="Repository name or local path")
    analyze_parser.add_argument("--max-candidates", type=int, default=None, help="Max candidates to analyze")
    analyze_parser.add_argument("--model", type=str, default=None)
    analyze_parser.add_argument("--output", type=str, default=None)

    args = parser.parse_args()

    if args.command == "perceive":
        coord = CoordinatorAgent(workspace_path=Path(args.workspace))
        state = coord.run_initial_perception(base_branch=args.base, target_branch=args.branch)
        if args.json:
            print(json.dumps(state.to_dict(), indent=2))
        else:
            print("\n" + "=" * 60)
            print("🛡️ DRIFTGUARD PHASE 1 PERCEPTION REPORT")
            print("=" * 60)
            print(f"  Workspace:       {state.workspace_path}")
            print(f"  Current Branch:  {state.delta_report.current_branch} (Targeted: {state.delta_report.is_branch_targeted})")
            print(f"  Base Reference:  {state.delta_report.base_branch}")
            print(f"  Files Changed:   {state.delta_report.total_files_changed}")
            if state.delta_report.added_files:
                print(f"    - Added:       {', '.join(state.delta_report.added_files)}")
            if state.delta_report.modified_files:
                print(f"    - Modified:    {', '.join(state.delta_report.modified_files)}")
            if state.delta_report.deleted_files:
                print(f"    - Deleted:     {', '.join(state.delta_report.deleted_files)}")
            print(f"  Detected Stack:  {', '.join(state.stack_report.detected_languages)} (Polyglot: {state.stack_report.is_polyglot})")
            print(f"  Components:      {len(state.stack_report.components)}")
            for c in state.stack_report.components:
                print(f"    • {c.name} ({c.primary_language}) in '{c.working_directory}'")
                print(f"      Build: {c.inferred_build_command or 'None'}")
                print(f"      Test:  {c.inferred_test_command or 'None'}")
            print("\n  Effective Build Matrix (with .driftguard.yml overrides):")
            for k, v in state.stack_report.effective_build_matrix.items():
                print(f"    [{k}] Build: {v.build_command!r} | Test: {v.test_command!r}")
            print(f"\n  Status:          {state.audit_status}")
            print("=" * 60 + "\n")

    elif args.command == "scan-stack":
        detector = StackDetector(workspace_path=Path(args.workspace))
        report = detector.detect_stack()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print("\n🔍 DRIFTGUARD AUTONOMOUS STACK DETECTION")
            print(f"  Languages:   {', '.join(report.detected_languages)}")
            print(f"  Is Polyglot: {report.is_polyglot}")
            print("  Components:")
            for c in report.components:
                print(f"    - {c.name} [{c.primary_language}]: frameworks={c.frameworks}, build={c.inferred_build_command!r}")
            print()

    elif args.command == "diff":
        scanner = GitDeltaScanner(workspace_path=Path(args.workspace))
        delta = scanner.scan_delta(base_branch=args.base)
        if args.json:
            print(json.dumps(delta.to_dict(), indent=2))
        else:
            print(f"\n🌿 GIT DELTA: {delta.current_branch} vs {delta.base_branch}")
            print(f"  Total Changed: {delta.total_files_changed} files")
            for f in delta.files:
                print(f"    [{f.status[:3]}] {f.path} ({len(f.modified_lines)} modified lines)")
            print()

    elif args.command == "config":
        cfg = DriftGuardConfig.load(Path(args.path) if args.path else None)
        print("✅ .driftguard.yml is valid.")
        if args.show:
            print("\n" + cfg.to_yaml())

    elif args.command == "ui":
        import subprocess
        ui_path = PROJECT_ROOT / "app" / "ui" / "streamlit_app.py"
        subprocess.run(["streamlit", "run", str(ui_path)])

    elif args.command == "analyze":
        # Fallback to existing analysis pipeline
        from app.ingestion.repository_ingestor import RepositoryIngestor
        from app.analysis.drift_pipeline import DriftPipeline

        workspace = Path(args.repository)
        if workspace.exists() and workspace.is_dir():
            ingestor = RepositoryIngestor()
            repo = ingestor.ingest_from_local(workspace)
            from app.ingestion.repository_scanner import RepositoryScanner
            scanner = RepositoryScanner()
            info = scanner.scan(repo)
            pipeline = DriftPipeline(workspace_path=workspace)
            res = pipeline.analyze_repository(info, max_candidates=args.max_candidates)
            print(f"Analysis Status: {res.get('status')}")
            print(f"Confirmed Drifts: {len(res.get('confirmed_drifts', []))}")
        else:
            print(f"Workspace not found: {args.repository}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

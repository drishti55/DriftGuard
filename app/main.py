#!/usr/bin/env python3
"""
DriftGuard Main Entry Point
Quick CLI for common operations.
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(
        description="DriftGuard — AI-Powered Cross-Artifact Consistency Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app/main.py analyze tiangolo/fastapi
  python app/main.py evaluate --mode baseline --sample-size 20
  python app/main.py ui
  python app/main.py list
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a repository")
    analyze_parser.add_argument("repository", help="Repository name")
    analyze_parser.add_argument("--max-candidates", "--max-pairs", type=int, default=None,
                                help="Max candidates to analyze (default: all)")
    analyze_parser.add_argument("--model", type=str, default=None)
    analyze_parser.add_argument("--output", type=str, default=None)

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Run evaluation")
    eval_parser.add_argument("--mode", choices=["baseline", "rag", "both", "compare"],
                             default="baseline")
    eval_parser.add_argument("--sample-size", type=int, default=None)
    eval_parser.add_argument("--model", type=str, default=None)

    # UI command
    subparsers.add_parser("ui", help="Launch Streamlit UI")

    # List command
    subparsers.add_parser("list", help="List available repositories")

    args = parser.parse_args()

    if args.command == "analyze":
        sys.argv = ["run_analysis.py", args.repository]
        if args.max_candidates:
            sys.argv.extend(["--max-candidates", str(args.max_candidates)])
        if args.model:
            sys.argv.extend(["--model", args.model])
        if args.output:
            sys.argv.extend(["--output", args.output])
        from scripts.run_analysis import main as run_analysis
        run_analysis()

    elif args.command == "evaluate":
        sys.argv = ["run_evaluation.py", "--mode", args.mode]
        if args.sample_size:
            sys.argv.extend(["--sample-size", str(args.sample_size)])
        if args.model:
            sys.argv.extend(["--model", args.model])
        from scripts.run_evaluation import main as run_eval
        run_eval()

    elif args.command == "ui":
        import subprocess
        ui_path = PROJECT_ROOT / "app" / "ui" / "streamlit_app.py"
        subprocess.run(["streamlit", "run", str(ui_path)])

    elif args.command == "list":
        from app.ingestion.repository_loader import RepositoryLoader
        loader = RepositoryLoader()
        repos = loader.list_available_repos()
        print(f"\nAvailable repositories ({len(repos)}):\n")
        for r in repos:
            print(f"  {r}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

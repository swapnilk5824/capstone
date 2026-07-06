#!/usr/bin/env python3
"""
CodeGuard CLI

Usage:
    python main.py review sample_data/pr_clean/pr.json
    CODEGUARD_MODE=live ANTHROPIC_API_KEY=sk-... python main.py review sample_data/pr_security/pr.json
    python main.py review sample_data/pr_missing_tests/pr.json --json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import run_review


def main():
    parser = argparse.ArgumentParser(description="CodeGuard multi-agent code review swarm")
    sub = parser.add_subparsers(dest="command", required=True)

    review_p = sub.add_parser("review", help="Run the review pipeline on a PR bundle JSON file")
    review_p.add_argument("pr_bundle", help="Path to a pr.json bundle")
    review_p.add_argument("--json", action="store_true", help="Print raw JSON result instead of the Markdown report")
    review_p.add_argument("--quiet", action="store_true", help="Suppress per-agent progress logs")

    args = parser.parse_args()

    if args.command == "review":
        mode = os.environ.get("CODEGUARD_MODE", "mock")
        print(f"CodeGuard running in {mode.upper()} mode\n", file=sys.stderr)
        result = run_review(args.pr_bundle, verbose=not args.quiet)

        if args.json:
            out = {k: v for k, v in result.items() if k != "_trace"}
            print(json.dumps(out, indent=2, default=str))
        else:
            print("\n" + result["report_markdown"])
            print(f"\n**Merge policy:** {result['merge_policy']}")


if __name__ == "__main__":
    main()

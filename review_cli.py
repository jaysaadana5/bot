#!/usr/bin/env python3
"""
CLI entry point for the AI Code Review Agent.

Usage:
    python review_cli.py file path/to/file.py
    python review_cli.py dir  src/
    python review_cli.py diff                      # reads from stdin
    python review_cli.py diff --git               # runs git diff automatically
    python review_cli.py self                      # review this project itself

Options:
    --no-ai          Disable AI-powered review (static analysis only)
    --severity LEVEL Minimum severity to report (CRITICAL|HIGH|MEDIUM|LOW|INFO)
    --json           Output raw JSON instead of formatted text
    --no-color       Disable colored output
"""

import argparse
import json
import subprocess
import sys

from code_review_agent import CodeReviewAgent, format_report


def main() -> None:
    """CLI entry point for the AI Code Review Agent."""
    # Shared flags available on every subcommand
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--no-ai", action="store_true", help="Static analysis only")
    shared.add_argument(
        "--severity",
        default="INFO",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
        help="Minimum severity to report",
    )
    shared.add_argument("--json", action="store_true", dest="json_output", help="Raw JSON output")
    shared.add_argument("--no-color", action="store_true", help="Disable colors")

    parser = argparse.ArgumentParser(
        description="AI Code Review Agent — >98% accuracy code reviews",
        parents=[shared],
    )
    subparsers = parser.add_subparsers(dest="command", help="Review mode")

    # --- file ---
    p_file = subparsers.add_parser("file", help="Review a single file", parents=[shared])
    p_file.add_argument("path", help="Path to the Python file")

    # --- dir ---
    p_dir = subparsers.add_parser("dir", help="Review a directory", parents=[shared])
    p_dir.add_argument("path", help="Path to the directory")
    p_dir.add_argument("--pattern", default="**/*.py", help="Glob pattern (default: **/*.py)")

    # --- diff ---
    p_diff = subparsers.add_parser("diff", help="Review a diff", parents=[shared])
    p_diff.add_argument("--git", action="store_true", help="Run git diff automatically")

    # --- self ---
    subparsers.add_parser("self", help="Review this project's own code", parents=[shared])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    agent = CodeReviewAgent(
        use_ai=not args.no_ai,
        severity_threshold=args.severity,
    )

    if args.command == "file":
        report = agent.review_file(args.path)
    elif args.command == "dir":
        report = agent.review_directory(args.path, pattern=args.pattern)
    elif args.command == "diff":
        if args.git:
            result = subprocess.run(
                ["git", "diff"], capture_output=True, text=True
            )
            diff_text = result.stdout
        else:
            diff_text = sys.stdin.read()
        report = agent.review_diff(diff_text)
    elif args.command == "self":
        report = agent.review_directory(".", pattern="*.py")
    else:
        parser.print_help()
        sys.exit(1)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report, colorize=not args.no_color))

    # Exit code: non-zero if critical or high issues found
    issues = report.get("issues", [])
    critical_high = [i for i in issues if i.get("severity") in ("CRITICAL", "HIGH")]
    sys.exit(1 if critical_high else 0)


if __name__ == "__main__":
    main()

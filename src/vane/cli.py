from __future__ import annotations

import argparse
import sys

from .config import COMPANIES
from .pipeline import daily, ingest, report, summarize
from .reporting import format_report, read_latest_report
from .spinner import run_with_spinner


def main(argv: list[str] | None = None) -> int:
    configure_output_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    if args.command == "help":
        print_full_help(parser)
        return 0

    try:
        if args.command == "ingest":
            paths = run_with_spinner("Fetching Bluesky posts and replies", lambda: ingest(args.date, args.company))
            print_paths("Wrote raw ingestion", paths)
        elif args.command == "summarize":
            paths = summarize(args.date, args.company)
            print_paths("Wrote snapshots", paths)
        elif args.command == "daily":
            raw_paths, snapshot_paths = run_with_spinner("Running daily ingestion and summarization", lambda: daily(args.date))
            print_paths("Wrote raw ingestion", raw_paths)
            print_paths("Wrote snapshots", snapshot_paths)
        elif args.command == "report":
            if args.last:
                path, latest = read_latest_report()
            else:
                path = run_with_spinner(
                    "Reasoning across snapshots",
                    lambda: report(args.date, days=args.days, triggered_by=args.trigger),
                )
                from .jsonio import read_json

                latest = read_json(path)
            print(format_report(latest, source_path=path))
            if not args.last:
                print(f"\nWrote report: {path}")
    except Exception as error:  # noqa: BLE001 - CLI should present concise failures.
        print(f"Vane stopped: {error}", file=sys.stderr)
        return 1
    return 0


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vane",
        description="Monitor narrative drift on Bluesky.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  vane help
  vane daily
  vane ingest --company openai
  vane summarize --company deepmind --date 2026-05-14
  vane report
  vane report --last
  vane report --days 9 --trigger manual
""",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("help", help="Show detailed help, examples, and subcommand flags.")

    ingest_parser = subparsers.add_parser("ingest", help="Fetch Bluesky posts and direct replies.")
    add_date_arg(ingest_parser)
    add_company_arg(ingest_parser)

    summarize_parser = subparsers.add_parser("summarize", help="Create daily JSON snapshots from raw ingestion files.")
    add_date_arg(summarize_parser)
    add_company_arg(summarize_parser)

    daily_parser = subparsers.add_parser("daily", help="Run ingestion and summarization for all companies.")
    add_date_arg(daily_parser)

    report_parser = subparsers.add_parser("report", help="Create a rolling narrative drift report.")
    add_date_arg(report_parser)
    report_parser.add_argument("--days", type=int, default=9, help="Rolling window size in days. Defaults to 9.")
    report_parser.add_argument(
        "--trigger",
        choices=("manual", "scheduled"),
        default="manual",
        help="How this report was triggered. Defaults to manual.",
    )
    report_parser.add_argument(
        "--last",
        action="store_true",
        help="Print the latest saved report without creating a new one.",
    )
    return parser


def add_date_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", help="UTC date to process, formatted YYYY-MM-DD. Defaults to today.")


def add_company_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--company",
        choices=("all", *(company.slug for company in COMPANIES)),
        default="all",
        help="Company slug to process. Defaults to all.",
    )


def print_paths(label: str, paths: list[object]) -> None:
    print(f"{label}:")
    for path in paths:
        print(f"  {path}")


def print_full_help(parser: argparse.ArgumentParser) -> None:
    parser.print_help()
    print("\nSubcommand details:\n")
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                if name == "help":
                    continue
                print(f"{name}")
                print("-" * len(name))
                subparser.print_help()
                print()

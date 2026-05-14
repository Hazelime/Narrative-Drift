from __future__ import annotations

import argparse
import sys

from .config import COMPANIES
from .pipeline import daily, ingest, report, summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vane", description="Monitor narrative drift on Bluesky.")
    subparsers = parser.add_subparsers(dest="command")

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

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    try:
        if args.command == "ingest":
            paths = ingest(args.date, args.company)
            print_paths("Wrote raw ingestion", paths)
        elif args.command == "summarize":
            paths = summarize(args.date, args.company)
            print_paths("Wrote snapshots", paths)
        elif args.command == "daily":
            raw_paths, snapshot_paths = daily(args.date)
            print_paths("Wrote raw ingestion", raw_paths)
            print_paths("Wrote snapshots", snapshot_paths)
        elif args.command == "report":
            path = report(args.date, days=args.days, triggered_by=args.trigger)
            print(f"Wrote report: {path}")
    except Exception as error:  # noqa: BLE001 - CLI should present concise failures.
        print(f"Vane stopped: {error}", file=sys.stderr)
        return 1
    return 0


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

"""Orchestration pipeline for the Vane Narrative Drift Tracker.

Defines tasks to query APIs (ingest), call LLM text summarization (summarize),
combine ingestion and summarization (daily), and synthesize multi-day cross-company
analytical reports (report).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from .bluesky import ingest_company
from .config import COMPANIES, RAW_DIR, REASONING_MODEL, REPORT_DIR, SNAPSHOT_DIR, SUMMARIZATION_MODEL, VERSION, CompanyConfig, company_by_slug
from .jsonio import read_json, write_json
from .llm import chat_json, chat_text, parse_json_object, strip_thinking
from .prompts import reasoning_messages, summarization_messages
from .timeutil import iso_now, parse_date


def raw_path(day: str, company_slug: str) -> Path:
    """Resolve the file system path for a raw API ingestion file.

    Args:
        day: ISO date string (YYYY-MM-DD).
        company_slug: Lowecase slug of the company.

    Returns:
        Path pointing to `data/raw/YYYY-MM-DD/company_slug.json`.
    """
    return RAW_DIR / day / f"{company_slug}.json"


def snapshot_path(day: str, company_slug: str) -> Path:
    """Resolve the file system path for a daily summarization snapshot.

    Args:
        day: ISO date string (YYYY-MM-DD).
        company_slug: Lowecase slug of the company.

    Returns:
        Path pointing to `data/snapshots/YYYY-MM-DD/company_slug.json`.
    """
    return SNAPSHOT_DIR / day / f"{company_slug}.json"


def ingest(day: str | None = None, company_slug: str | None = None) -> list[Path]:
    """Fetch raw post records from Bluesky and save them to the filesystem.

    Args:
        day: Optional ISO date string targeting the run. Defaults to today's date.
        company_slug: Optional slug filter to run ingestion for a single company.
                      If None or 'all', ingests all configured companies.

    Returns:
        List of Path objects where raw JSON files were written.
    """
    target_day = parse_date(day).isoformat()
    written: list[Path] = []
    for company in select_companies(company_slug):
        data = ingest_company(company)
        data = {"date": target_day, **data}
        path = raw_path(target_day, company.slug)
        write_json(path, data)
        written.append(path)
    return written


def summarize(day: str | None = None, company_slug: str | None = None) -> list[Path]:
    """Call the LLM summarizer to compress previously ingested raw data into daily snapshots.

    Args:
        day: Optional ISO date string representing the target raw folder. Defaults to today.
        company_slug: Optional company slug filter. Defaults to all companies.

    Returns:
        List of Path objects where summarized daily snapshot JSON files were written.

    Raises:
        FileNotFoundError: If the raw ingestion file for the target day does not exist.
    """
    target_day = parse_date(day).isoformat()
    written: list[Path] = []
    for company in select_companies(company_slug):
        path = raw_path(target_day, company.slug)
        if not path.exists():
            raise FileNotFoundError(f"Missing raw ingestion file: {path}")
        raw = read_json(path)
        summary = chat_json(
            model=SUMMARIZATION_MODEL,
            messages=summarization_messages(raw),
            temperature=0.2,
            max_tokens=4096,
        )
        snapshot = {
            "date": target_day,
            "company": company.label,
            "company_slug": company.slug,
            "ingested_at": raw.get("ingested_at"),
            "post_count": raw.get("post_count", 0),
            "reply_count": raw.get("reply_count", 0),
            "summarization_model": SUMMARIZATION_MODEL,
            "version": VERSION,
            "snapshot": summary,
        }
        output = snapshot_path(target_day, company.slug)
        write_json(output, snapshot)
        written.append(output)
    return written


def daily(day: str | None = None) -> tuple[list[Path], list[Path]]:
    """Execute both ingestion and summarization for all companies sequentially for a given day.

    Args:
        day: Optional ISO date string. Defaults to today.

    Returns:
        A tuple containing (list of raw paths, list of snapshot paths) written.
    """
    target_day = parse_date(day).isoformat()
    raw_files = ingest(target_day)
    snapshot_files = summarize(target_day)
    return raw_files, snapshot_files


def report(day: str | None = None, *, days: int = 9, triggered_by: str = "manual") -> Path:
    """Analyze snapshots across a rolling window and generate a narrative drift report.

    Queries the LLM reasoning model to identify trajectories, cross-company contrasts,
    causal event drivers, and language shifts across the target date range.

    Args:
        day: Optional end-date of the rolling window. Defaults to the latest available snapshot date.
        days: Size of the rolling window in days. Defaults to 9.
        triggered_by: String label denoting invocation mode ('manual' or 'scheduled').

    Returns:
        The Path to the newly written report JSON file.

    Raises:
        FileNotFoundError: If no snapshots are found in the target window.
    """
    end_day = parse_date(day) if day else parse_date(latest_snapshot_day())
    start_day = end_day - timedelta(days=days - 1)
    snapshots = load_snapshots(start_day.isoformat(), end_day.isoformat())
    if not snapshots:
        raise FileNotFoundError(f"No snapshots found from {start_day.isoformat()} through {end_day.isoformat()}.")

    generated_at = iso_now()
    content = chat_text(
        model=REASONING_MODEL,
        messages=reasoning_messages(snapshots, triggered_by=triggered_by, generated_at=generated_at),
        temperature=0.2,
        max_tokens=8192,
    )
    parsed = parse_json_object(strip_thinking(content))
    parsed["metadata"] = {
        "generated_at": generated_at,
        "period": {"start_date": start_day.isoformat(), "end_date": end_day.isoformat()},
        "snapshots_analyzed": len(snapshots),
        "model": REASONING_MODEL,
        "triggered_by": triggered_by,
        "version": VERSION,
    }
    output = REPORT_DIR / f"{next_report_number():03d}_{end_day.isoformat()}.json"
    write_json(output, parsed)
    return output


def load_snapshots(start_day: str, end_day: str) -> list[dict[str, Any]]:
    """Load and sort all daily snapshot files within an inclusive date range.

    Args:
        start_day: Start date string (YYYY-MM-DD).
        end_day: End date string (YYYY-MM-DD).

    Returns:
        A sorted list of snapshot dictionary contents.
    """
    snapshots: list[dict[str, Any]] = []
    for path in sorted(SNAPSHOT_DIR.glob("*/*.json")):
        if not path.is_file():
            continue
        day = path.parent.name
        if start_day <= day <= end_day:
            snapshots.append(read_json(path))
    snapshots.sort(key=lambda item: (item.get("date", ""), item.get("company_slug", "")))
    return snapshots


def next_report_number() -> int:
    """Determine the next sequential report number prefix by scanning existing files.

    Scans the `reports` directory, parses digits from names like '002_2026-05-18.json',
    and increments the highest number found.

    Returns:
        The integer code for the next report (e.g. 3).
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    highest = 0
    for path in REPORT_DIR.glob("*.json"):
        prefix = path.stem.split("_", 1)[0]
        if prefix.isdigit():
            highest = max(highest, int(prefix))
    return highest + 1


def latest_snapshot_day() -> str | None:
    """Find the date string of the most recent snapshot directory containing files.

    Returns:
        The YYYY-MM-DD date string of the latest snapshot, or None if no snapshots exist.
    """
    days = sorted({path.parent.name for path in SNAPSHOT_DIR.glob("*/*.json") if path.is_file()})
    return days[-1] if days else None


def select_companies(company_slug: str | None) -> tuple[CompanyConfig, ...]:
    """Helper to select either all companies or a single company config by slug.

    Args:
        company_slug: The target company slug, or 'all', or None.

    Returns:
        A tuple of selected CompanyConfig objects.
    """
    if not company_slug or company_slug == "all":
        return COMPANIES
    return (company_by_slug(company_slug),)

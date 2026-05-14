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
    return RAW_DIR / day / f"{company_slug}.json"


def snapshot_path(day: str, company_slug: str) -> Path:
    return SNAPSHOT_DIR / day / f"{company_slug}.json"


def ingest(day: str | None = None, company_slug: str | None = None) -> list[Path]:
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
    target_day = parse_date(day).isoformat()
    raw_files = ingest(target_day)
    snapshot_files = summarize(target_day)
    return raw_files, snapshot_files


def report(day: str | None = None, *, days: int = 9, triggered_by: str = "manual") -> Path:
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
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    highest = 0
    for path in REPORT_DIR.glob("*.json"):
        prefix = path.stem.split("_", 1)[0]
        if prefix.isdigit():
            highest = max(highest, int(prefix))
    return highest + 1


def latest_snapshot_day() -> str | None:
    days = sorted({path.parent.name for path in SNAPSHOT_DIR.glob("*/*.json") if path.is_file()})
    return days[-1] if days else None


def select_companies(company_slug: str | None) -> tuple[CompanyConfig, ...]:
    if not company_slug or company_slug == "all":
        return COMPANIES
    return (company_by_slug(company_slug),)

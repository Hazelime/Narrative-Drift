from __future__ import annotations

from datetime import UTC, date, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_date(value: str | None) -> date:
    if not value:
        return utc_now().date()
    return date.fromisoformat(value)

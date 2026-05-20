"""Date and time utilities configured for UTC operations.

Provides helpers for querying current times, formatting timestamps, and parsing
ISO-formatted date arguments supplied via the CLI or schedules.
"""

from __future__ import annotations

from datetime import UTC, date, datetime


def utc_now() -> datetime:
    """Get the current datetime object localized in the UTC timezone.

    Returns:
        A datetime instance representing current UTC time.
    """
    return datetime.now(UTC)


def iso_now() -> str:
    """Format the current UTC date and time into an ISO 8601 string.

    Uses the 'Z' suffix to denote UTC (e.g., '2026-05-19T14:57:00Z').

    Returns:
        An ISO 8601 formatted datetime string.
    """
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_date(value: str | None) -> date:
    """Parse a YYYY-MM-DD date string, defaulting to current UTC date if empty.

    Args:
        value: Optional date string in YYYY-MM-DD ISO format.

    Returns:
        A date object corresponding to the parsed string or today's UTC date.

    Raises:
        ValueError: If value is not a valid ISO date string.
    """
    if not value:
        return utc_now().date()
    return date.fromisoformat(value)

"""Formatting and representation utilities for Vane reports.

Converts structured, machine-readable report JSON files into readable,
formatted plain-text/markdown summaries for CLI and user inspection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import REPORT_DIR
from .jsonio import read_json


def latest_report_path() -> Path | None:
    """Find the path of the most recently written report JSON file in the reports directory.

    Scans the `reports` directory and returns the last sorted filename.

    Returns:
        The Path to the latest report file, or None if no reports exist.
    """
    reports = sorted(REPORT_DIR.glob("*.json"))
    return reports[-1] if reports else None


def format_report(report: dict[str, Any], *, source_path: Path | None = None) -> str:
    """Translate a report dictionary into an academic, human-readable text string.

    Organizes metadata, company-specific narratives, meta-observations,
    historical trajectory summary tables, comparative findings, vocabulary
    drifts, and uncertainties into structured sections.

    Args:
        report: The dictionary representing the parsed JSON report content.
        source_path: Optional Path to print the source filename in metadata.

    Returns:
        A multi-line formatted report string.
    """
    metadata = report.get("metadata") or {}
    narrative = report.get("narrative") or {}
    drift = report.get("drift_summary") or {}
    findings = report.get("comparative_findings") or []
    vocabulary = report.get("vocabulary_drift") or {}
    uncertainties = report.get("uncertainties") or []

    lines: list[str] = []
    lines.append("Vane Narrative Drift Report")
    lines.append("=" * 28)
    if source_path:
        lines.append(f"File: {source_path}")
    lines.append(f"Generated: {metadata.get('generated_at', 'unknown')}")
    period = metadata.get("period") or {}
    lines.append(f"Period: {period.get('start_date', 'unknown')} to {period.get('end_date', 'unknown')}")
    lines.append(f"Snapshots analyzed: {metadata.get('snapshots_analyzed', 'unknown')}")
    lines.append(f"Model: {metadata.get('model', 'unknown')}")
    lines.append(f"Triggered by: {metadata.get('triggered_by', 'unknown')}")

    lines.extend(["", "Narrative", "-" * 9])
    for key, label in (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("deepmind", "Google DeepMind")):
        value = narrative.get(key)
        if value:
            lines.extend(["", f"{label}: {value}"])
    meta_observations = narrative.get("meta_observations") or []
    for observation in meta_observations[:2]:
        lines.extend(["", f"Meta-observation: {observation}"])

    if drift:
        lines.extend(["", "Drift Summary", "-" * 13])
        for key, label in (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("deepmind", "Google DeepMind")):
            item = drift.get(key) or {}
            if not item:
                continue
            lines.extend(
                [
                    "",
                    f"{label}",
                    f"  Trajectory: {item.get('trajectory', 'unknown')} ({item.get('confidence', 'unknown')} confidence)",
                    f"  Key shift: {item.get('key_shift', 'unknown')}",
                    f"  Shift start: {item.get('shift_start', 'unknown')}",
                    f"  Primary driver: {item.get('primary_driver', 'unknown')}",
                ]
            )

    if findings:
        lines.extend(["", "Comparative Findings", "-" * 20])
        for index, finding in enumerate(findings, start=1):
            if isinstance(finding, dict):
                text = finding.get("finding", "unknown")
                confidence = finding.get("confidence", "unknown")
                lines.append(f"{index}. {text} ({confidence} confidence)")
            else:
                lines.append(f"{index}. {finding}")

    emerging = vocabulary.get("emerging") or []
    fading = vocabulary.get("fading") or []
    if emerging or fading:
        lines.extend(["", "Vocabulary Drift", "-" * 16])
        lines.append(f"Emerging: {', '.join(emerging) if emerging else 'none noted'}")
        lines.append(f"Fading: {', '.join(fading) if fading else 'none noted'}")

    if uncertainties:
        lines.extend(["", "Uncertainties", "-" * 13])
        for uncertainty in uncertainties:
            lines.append(f"- {uncertainty}")

    return "\n".join(lines)


def read_latest_report() -> tuple[Path, dict[str, Any]]:
    """Retrieve and read the most recent narrative report file.

    Returns:
        A tuple of (Path to report, deserialized report dictionary).

    Raises:
        FileNotFoundError: If no reports are found in the reports directory.
    """
    path = latest_report_path()
    if not path:
        raise FileNotFoundError("No reports found in data/reports.")
    return path, read_json(path)

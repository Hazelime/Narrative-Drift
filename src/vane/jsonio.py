"""JSON file and formatting utility functions.

Encapsulates file reads and writes with consistent UTF-8 encoding, automatic
parent directory creation, formatted output indentation, and compact dumps
for embedding JSON payloads within LLM prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """Read a JSON file and return the parsed Python structure.

    Args:
        path: Path object specifying the file to read.

    Returns:
        The decoded JSON content (typically a dictionary or list).
    """
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    """Write data to a file as formatted JSON, creating parent directories if needed.

    Ensures consistent formatting (2-space indent, preserved key order, UTF-8,
    and a trailing newline character).

    Args:
        path: Path object specifying where to save the file.
        data: The serializable Python data to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def compact_json(data: Any) -> str:
    """Serialize data into a single-line, compact JSON string.

    Useful for minimizing tokens when inserting raw data into LLM prompts.

    Args:
        data: The serializable Python data to convert.

    Returns:
        A compact JSON representation with whitespaces removed.
    """
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

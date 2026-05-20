"""HTTP networking utilities using the Python standard library.

Provides lightweight wrappers around `urllib` to make GET and POST requests
and exchange JSON data with external APIs without third-party dependencies.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class VaneHttpError(RuntimeError):
    """Raised when an HTTP request fails or returns an error status code."""


def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    """Send a GET request to the specified URL and return the parsed JSON response.

    Args:
        url: The API endpoint URL.
        params: Query parameters to append to the URL (null values are filtered out).
        headers: Optional HTTP headers to include in the request.

    Returns:
        The decoded JSON response (typically a dictionary or list).

    Raises:
        VaneHttpError: If the request fails or encounters a network issue.
    """
    if params:
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers=headers or {})
    return _request_json(request)


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    """Send a POST request with a JSON payload and return the parsed JSON response.

    Args:
        url: The API endpoint URL.
        payload: Python dictionary to serialize into the JSON request body.
        headers: Optional HTTP headers to merge with the default JSON headers.

    Returns:
        The decoded JSON response (typically a dictionary or list).

    Raises:
        VaneHttpError: If the request fails or encounters a network issue.
    """
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    return _request_json(request)


def _request_json(request: urllib.request.Request) -> Any:
    """Execute a urllib Request, handle timeouts, and decode the JSON response.

    Args:
        request: The prepared urllib request.

    Returns:
        The decoded JSON object from the response body.

    Raises:
        VaneHttpError: If the HTTP request returns an error code or times out.
    """
    try:
        # Default to a 60-second timeout to handle slow API responses gracefully
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise VaneHttpError(f"HTTP {error.code} from {request.full_url}: {body}") from error
    except urllib.error.URLError as error:
        raise VaneHttpError(f"Network error for {request.full_url}: {error.reason}") from error

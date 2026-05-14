from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class VaneHttpError(RuntimeError):
    pass


def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    if params:
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers=headers or {})
    return _request_json(request)


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    return _request_json(request)


def _request_json(request: urllib.request.Request) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise VaneHttpError(f"HTTP {error.code} from {request.full_url}: {body}") from error
    except urllib.error.URLError as error:
        raise VaneHttpError(f"Network error for {request.full_url}: {error.reason}") from error

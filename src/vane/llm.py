from __future__ import annotations

import json
import os
from typing import Any

from .config import BERGET_BASE_URL
from .http import post_json


class VaneLlmError(RuntimeError):
    pass


def chat_json(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    content = chat_text(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return parse_json_object(content)


def chat_text(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 4096,
    response_format: dict[str, Any] | None = None,
) -> str:
    api_key = resolve_api_key()
    base_url = resolve_base_url().rstrip("/")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    response = post_json(
        f"{base_url}/chat/completions",
        payload,
        {"Authorization": f"Bearer {api_key}"},
    )
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise VaneLlmError(f"Unexpected LLM response shape: {response}") from error


def resolve_api_key() -> str:
    api_key = os.getenv("VANE_API_KEY") or os.getenv("BERGET_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise VaneLlmError("Missing API key. Set VANE_API_KEY, BERGET_API_KEY, or OPENAI_API_KEY.")
    return api_key


def resolve_base_url() -> str:
    return os.getenv("VANE_BASE_URL") or os.getenv("BERGET_BASE_URL") or os.getenv("OPENAI_BASE_URL") or BERGET_BASE_URL


def parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = json.loads(extract_first_json_object(cleaned))
    if not isinstance(parsed, dict):
        raise VaneLlmError("Expected the model to return a JSON object.")
    return parsed


def strip_thinking(content: str) -> str:
    cleaned = content.strip()
    while "<thinking>" in cleaned and "</thinking>" in cleaned:
        before, rest = cleaned.split("<thinking>", 1)
        _, after = rest.split("</thinking>", 1)
        cleaned = f"{before}{after}".strip()
    return cleaned


def extract_first_json_object(content: str) -> str:
    start = content.find("{")
    if start < 0:
        raise VaneLlmError("No JSON object found in model output.")
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(content[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    raise VaneLlmError("JSON object in model output was not closed.")

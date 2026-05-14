from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
REPORT_DIR = DATA_DIR / "reports"

BLUESKY_BASE_URL = "https://api.bsky.app"
BERGET_BASE_URL = "https://api.berget.ai/v1"

SUMMARIZATION_MODEL = "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
REASONING_MODEL = "openai/gpt-oss-120b"
VERSION = "1.0"


@dataclass(frozen=True)
class CompanyConfig:
    slug: str
    label: str
    company_query: str
    service_query: str


COMPANIES: tuple[CompanyConfig, ...] = (
    CompanyConfig("openai", "OpenAI", "OpenAI", "ChatGPT"),
    CompanyConfig("anthropic", "Anthropic", "Anthropic", "Claude"),
    CompanyConfig("deepmind", "Google DeepMind", "DeepMind", "Gemini"),
)


GEMINI_AI_CONTEXT_WORDS = (
    "ai",
    "artificial intelligence",
    "llm",
    "model",
    "models",
    "google",
    "deepmind",
    "claude",
    "anthropic",
    "openai",
    "chatgpt",
    "prompt",
    "prompts",
    "api",
    "agent",
    "agents",
    "assistant",
    "reasoning",
    "benchmark",
    "tokens",
    "context window",
    "multimodal",
    "generative",
    "bard",
    "workspace",
    "veo",
    "imagen",
    "notebooklm",
    "ai studio",
    "deep research",
)


def company_by_slug(slug: str) -> CompanyConfig:
    for company in COMPANIES:
        if company.slug == slug:
            return company
    known = ", ".join(company.slug for company in COMPANIES)
    raise ValueError(f"Unknown company '{slug}'. Expected one of: {known}")

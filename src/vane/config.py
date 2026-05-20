"""Configuration settings and constants for Vane.

Defines workspace paths, API endpoints, default model identifiers, target companies,
and filtering heuristics (such as the context words for Gemini disambiguation).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Directory structure configurations
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
REPORT_DIR = DATA_DIR / "reports"

# External API service base URLs
BLUESKY_BASE_URL = "https://api.bsky.app"
BERGET_BASE_URL = "https://api.berget.ai/v1"

# LLM configurations for the two pipeline phases
SUMMARIZATION_MODEL = "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
REASONING_MODEL = "openai/gpt-oss-120b"
VERSION = "1.0"


@dataclass(frozen=True)
class CompanyConfig:
    """Configuration schema for a monitored organization.

    Attributes:
        slug: Short alphanumeric identifier used in paths and CLI commands.
        label: Human-readable name of the organization.
        company_query: Search query used for general company mentions.
        service_query: Search query used for the company's primary AI service.
    """
    slug: str
    label: str
    company_query: str
    service_query: str


# Monitored companies and their queries
COMPANIES: tuple[CompanyConfig, ...] = (
    CompanyConfig("openai", "OpenAI", "OpenAI", "ChatGPT"),
    CompanyConfig("anthropic", "Anthropic", "Anthropic", "Claude"),
    CompanyConfig("deepmind", "Google DeepMind", "DeepMind", "Gemini"),
)


# Keywords used to heuristically filter Google DeepMind's 'Gemini' search results.
# Because 'Gemini' is a polysemous word (astrology, crypto, etc.), we only keep
# posts that also mention at least one of these AI-specific or organization-specific terms.
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
    """Retrieve a CompanyConfig by its unique slug identifier.

    Args:
        slug: The lowercase string slug identifying the company.

    Returns:
        The matching CompanyConfig object.

    Raises:
        ValueError: If the slug does not match any configured company.
    """
    for company in COMPANIES:
        if company.slug == slug:
            return company
    known = ", ".join(company.slug for company in COMPANIES)
    raise ValueError(f"Unknown company '{slug}'. Expected one of: {known}")

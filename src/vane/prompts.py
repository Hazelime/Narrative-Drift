from __future__ import annotations

from typing import Any

from .jsonio import compact_json


SUMMARIZATION_SYSTEM = """You are Vane, an analytical narrative drift monitor.
Compress Bluesky posts and direct replies into a structured JSON snapshot.
Be analytical rather than descriptive: infer how topics are being framed, what comparisons are implied, and what vocabulary signals may matter later.
Do not overstate weak evidence. Note non-English content when it is significant.
Return only a JSON object."""


def summarization_messages(raw_ingestion: dict[str, Any]) -> list[dict[str, str]]:
    company = raw_ingestion["company"]
    content = f"""Summarize this Bluesky ingestion set for {company}.

Use this JSON shape:
{{
  "dominant_themes": [
    {{
      "theme": "short label",
      "analytical_framing": "what the discussion suggests about perception",
      "evidence_uris": ["at://..."],
      "strength": "strong|medium|weak"
    }}
  ],
  "sentiment_toward_company": {{
    "label": "positive|mixed|negative|neutral|unclear",
    "rationale": "short analytical explanation",
    "confidence": "high|medium|low"
  }},
  "notable_events_mentioned": [
    {{
      "event": "what happened or was alleged",
      "company_relevance": "why it mattered",
      "evidence_uris": ["at://..."]
    }}
  ],
  "cross_company_comparisons": [
    {{
      "companies": ["OpenAI", "Anthropic"],
      "comparison": "how they were contrasted",
      "evidence_uris": ["at://..."]
    }}
  ],
  "high_signal_posts": [
    {{
      "uri": "at://...",
      "why_high_signal": "why this post/reply is unusually useful",
      "claim_or_frame": "the key claim or frame"
    }}
  ],
  "vocabulary_signals": {{
    "emerging_terms": ["term"],
    "repeated_phrases": ["phrase"],
    "descriptors": ["descriptor"]
  }},
  "non_english_content": {{
    "significant": true,
    "languages_or_regions": ["unknown if uncertain"],
    "notes": "brief note"
  }},
  "caveats": ["limitations of this snapshot"]
}}

Raw ingestion JSON:
{compact_json(raw_ingestion)}
"""
    return [
        {"role": "system", "content": SUMMARIZATION_SYSTEM},
        {"role": "user", "content": content},
    ]


REASONING_SYSTEM = """You are Vane, an honest narrative drift analyst.
Reason across rolling daily snapshots for OpenAI, Anthropic, and Google DeepMind.
Distinguish strong from weak signals, explicitly state confidence, and treat relative drift as just as important as absolute drift.
The highest confidence requires support from at least 3 consecutive snapshots.
Before the final JSON, write a short scratchpad section enclosed in <thinking>...</thinking>. It will be discarded by the caller.
After that, output exactly one JSON object and no other prose."""


def reasoning_messages(snapshots: list[dict[str, Any]], *, triggered_by: str, generated_at: str) -> list[dict[str, str]]:
    content = f"""Generate a narrative drift report from these snapshots.

Reason in these steps before producing JSON:
1. Baseline: What is the current narrative for each company?
2. Historical comparison: How has the narrative changed over the past 9 days if available, and when did the shift begin?
3. Cross-company contrasts: Where do the three narratives diverge?
4. Causal reasoning: What specific events or vocabulary patterns appear to have caused shifts?
5. Confidence: Which findings are well-supported and which are uncertain?

Remember that posts primarily associated with one company can contain signals about another company.

Return this JSON shape:
{{
  "metadata": {{
    "generated_at": "{generated_at}",
    "period": {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}},
    "snapshots_analyzed": 0,
    "model": "model id",
    "triggered_by": "{triggered_by}",
    "version": "1.0"
  }},
  "narrative": {{
    "openai": "one paragraph",
    "anthropic": "one paragraph",
    "deepmind": "one paragraph",
    "meta_observations": ["optional paragraph 1", "optional paragraph 2"]
  }},
  "drift_summary": {{
    "openai": {{
      "trajectory": "improving|declining|stable|volatile|unclear",
      "confidence": "high|medium|low",
      "key_shift": "short description",
      "shift_start": "YYYY-MM-DD or unknown",
      "primary_driver": "short description"
    }},
    "anthropic": {{
      "trajectory": "improving|declining|stable|volatile|unclear",
      "confidence": "high|medium|low",
      "key_shift": "short description",
      "shift_start": "YYYY-MM-DD or unknown",
      "primary_driver": "short description"
    }},
    "deepmind": {{
      "trajectory": "improving|declining|stable|volatile|unclear",
      "confidence": "high|medium|low",
      "key_shift": "short description",
      "shift_start": "YYYY-MM-DD or unknown",
      "primary_driver": "short description"
    }}
  }},
  "comparative_findings": [
    {{
      "finding": "cross-company pattern",
      "confidence": "high|medium|low",
      "evidence": ["brief evidence references"]
    }}
  ],
  "vocabulary_drift": {{
    "emerging": ["word or phrase"],
    "fading": ["word or phrase"]
  }},
  "uncertainties": ["important caveats"]
}}

Snapshots:
{compact_json(snapshots)}
"""
    return [
        {"role": "system", "content": REASONING_SYSTEM},
        {"role": "user", "content": content},
    ]

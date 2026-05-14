# Narrative Drift

Vane monitors narrative drift around OpenAI, Anthropic, and Google DeepMind on the [Bluesky](https://bsky.app/) social media service, then reasons about how those narratives change over time using [Berget.ai](https://berget.ai/) AI inference.

Narrative drift means a detectable change in how people frame a company: what they praise, criticize, compare, joke about, worry about, or treat as newly important. This can be interesting because public perception often moves before it becomes visible in formal media coverage, surveys, or market analysis. Vane is designed to catch those softer shifts: not just "people mentioned coding," but "coding performance is being framed as Anthropic's differentiator against OpenAI."

The GitHub version runs automatically: daily collection and summarization happen at 23:52 UTC, and narrative reports are generated every third day from the latest rolling window. Reports can also be generated manually whenever you run `vane report` or trigger the report workflow.

## How It Works

Vane has five layers:

1. Ingest top Bluesky posts for each company and associated service.
2. Summarize each company/day into a structured JSON snapshot.
3. Store raw ingestions, snapshots, and reports as flat JSON files.
4. Reason across a rolling 9-day window.
5. Save a machine-readable report with human-readable narrative paragraphs.

Each ingestion run searches for:

- `OpenAI` and `ChatGPT`
- `Anthropic` and `Claude`
- `DeepMind` and `Gemini`

For each company, Vane fetches the top 100 company posts and the top 100 service posts, deduplicates them by Bluesky URI, sorts them by engagement, and keeps the top 50. Engagement is scored as:

```text
likeCount + 3*repostCount + 4*replyCount + 5*quoteCount
```

For each kept post, Vane fetches up to 3 direct replies, sorted by like count. A full run therefore makes up to 156 Bluesky API calls: 6 search calls plus 150 thread calls. The maximum stored content is 150 top-level posts plus up to 450 direct replies per ingestion run.

## Gemini Filtering

`Gemini` receives special treatment because it is not only an AI product name. It can also refer to astrology, crypto, NASA missions, music, usernames, and other unrelated topics. Vane still fetches broad `Gemini` results, but it filters them client-side to keep posts that contain AI-context terms such as `AI`, `LLM`, `model`, `Google`, `DeepMind`, `Claude`, `OpenAI`, `ChatGPT`, `prompt`, or `API`.

This keeps the search broad enough to catch unexpected phrasing while reducing obvious non-AI noise before summarization.

## Reasoning Style

Daily snapshots are compressed descriptions of what happened in one day's posts. Reports are more interpretive: Vane compares snapshots across a rolling window and asks what changed, when the shift began, what may have caused it, and how strong the evidence is.

Vane reasons in five steps:

1. Establish the current baseline narrative for each company.
2. Compare that baseline with the previous 9 days when available.
3. Contrast the three companies against each other.
4. Identify likely drivers, including events and vocabulary changes.
5. Assign confidence while separating strong signals from weak ones.

Example report-style output might look like this:

```text
OpenAI: The narrative remained high-attention but more contested, with users framing ChatGPT as the default product while comparing its coding reliability against Claude. Confidence is medium because the comparison appeared across several high-engagement posts but has not yet persisted for three consecutive snapshots.

Anthropic: Claude was framed less as a general chatbot and more as a practical work tool, especially for coding and long-context tasks. The key shift appears to be a stronger "professional reliability" frame.

Vocabulary drift: emerging terms include "agentic", "coding benchmark", and "context window"; fading terms include older launch-specific language.
```

## Setup

Vane uses the OpenAI-compatible [Berget.ai](https://berget.ai/) inference API. Set one of these environment variables:

```powershell
$env:BERGET_API_KEY = "your-key"
```

Optional overrides:

```powershell
$env:BERGET_BASE_URL = "https://api.berget.ai/v1"
$env:VANE_API_KEY = "your-key"
$env:VANE_BASE_URL = "https://api.berget.ai/v1"
```

Install locally:

```powershell
python -m pip install -e .
```

If `vane` is not on PATH after installation, run commands with:

```powershell
python -m vane help
```

## Commands

Show detailed help, including flags and narrower commands:

```powershell
vane help
```

Run ingestion and summarization for all three companies:

```powershell
vane daily
```

Fetch raw Bluesky posts only:

```powershell
vane ingest
vane ingest --company openai
vane ingest --company anthropic --date 2026-05-14
```

Summarize already-ingested raw data:

```powershell
vane summarize
vane summarize --company deepmind
```

Create and print a rolling narrative drift report:

```powershell
vane report
```

Print the latest saved report without creating a new one:

```powershell
vane report --last
```

Use a different rolling window:

```powershell
vane report --days 12
```

All dates are UTC. When no report date is supplied, reporting uses the latest available snapshot date.

## Data Layout

Raw Bluesky ingestions:

```text
data/raw/YYYY-MM-DD/company.json
```

Daily snapshots:

```text
data/snapshots/YYYY-MM-DD/company.json
```

Reports:

```text
data/reports/NNN_YYYY-MM-DD.json
```

## Models

Summarization uses:

```text
mistralai/Mistral-Small-3.2-24B-Instruct-2506
```

Reasoning uses:

```text
openai/gpt-oss-120b
```

The model split is intentional. Summarization is frequent, repetitive, and mostly compression-oriented, so Mistral Small keeps daily costs low while still supporting structured JSON output. Reasoning happens less often and benefits from a larger model that can compare multiple snapshots, distinguish weak from strong evidence, and produce a cautious cross-company interpretation.

[Berget.ai's model library](https://berget.ai/models) describes its model selection as balancing performance, speed, and cost, with emphasis on open models and European AI sovereignty. Current public pricing indexed from Berget shows `mistralai/Mistral-Small-3.2-24B-Instruct-2506` at about $0.33 per 1M input tokens and $0.33 per 1M output tokens, and `openai/gpt-oss-120b` at about $0.44 per 1M input tokens and $0.99 per 1M output tokens.

In practice, cost depends on post length and reply length. A typical run is expected to be small: three summarization calls per ingestion day, plus one reasoning call every third day. A rough operating range is about $1-$5 per month for normal scheduled use, with the lower end more likely when posts are short and reports are generated every third day rather than daily. Heavy manual reruns, unusually long posts, or expanded windows will increase cost.

## GitHub Actions

Add `BERGET_API_KEY` as a repository secret.

The included workflows:

- Run ingestion and summarization daily at 23:52 UTC.
- Run reporting every third calendar day and on manual dispatch.
- Commit generated JSON files back to the repository.

Reports are therefore generated both automatically on schedule and manually when prompted.

Never commit API keys. `.env` is ignored.

## Sources

- [Bluesky](https://bsky.app/)
- [Bluesky API documentation](https://docs.bsky.app/)
- [Berget.ai](https://berget.ai/)
- [Berget.ai model library](https://berget.ai/models)
- [Berget.ai model pricing index](https://llm24.net/provider/berget)

"""Bluesky API client for search ingestion, deduplication, and engagement scoring.

Queries the Bluesky API for posts mentioning monitored companies or services,
normalizes and deduplicates results, scores them by engagement weights, filters
polysemous terms (Gemini) using AI keywords, and fetches direct thread replies.
"""

from __future__ import annotations

from typing import Any

from .config import BLUESKY_BASE_URL, CompanyConfig, GEMINI_AI_CONTEXT_WORDS
from .http import get_json
from .timeutil import iso_now


def engagement_score(post: dict[str, Any]) -> int:
    """Calculate the custom weighted engagement score for a post.

    The score weights metrics by visibility/virality impact:
    `likes + 3 * reposts + 4 * replies + 5 * quotes`

    Args:
        post: A normalized post dictionary containing counts.

    Returns:
        The integer engagement score.
    """
    return (
        1 * int(post.get("like_count") or 0)
        + 3 * int(post.get("repost_count") or 0)
        + 4 * int(post.get("reply_count") or 0)
        + 5 * int(post.get("quote_count") or 0)
    )


def ingest_company(company: CompanyConfig, *, limit_per_query: int = 100, keep_posts: int = 50) -> dict[str, Any]:
    """Ingest top Bluesky posts and replies for a specific company configuration.

    Runs search queries for both the company and its primary service, merges and
    deduplicates the results, sorts them by engagement score, keeps the top posts,
    and fetches up to 3 direct replies for each kept post.

    Args:
        company: The CompanyConfig object containing search queries and labels.
        limit_per_query: Max number of raw posts to request per search API call.
        keep_posts: The number of top engagement posts to preserve after deduplication.

    Returns:
        A dictionary containing ingestion metadata, API call counts, and the
        list of normalized, reply-threaded posts.
    """
    search_calls = 0
    thread_calls = 0
    notes: list[str] = []

    # 1. Fetch general company mentions (e.g. "OpenAI")
    company_posts = search_posts(company.company_query, limit=limit_per_query)
    search_calls += 1

    # 2. Fetch primary service mentions (e.g. "ChatGPT")
    service_posts = search_posts(company.service_query, limit=limit_per_query)
    search_calls += 1

    # 3. Apply Gemini disambiguation heuristic if the service is Gemini
    if company.service_query.lower() == "gemini":
        before = len(service_posts)
        service_posts = [post for post in service_posts if is_ai_context_post(post)]
        notes.append(f"Filtered Gemini service posts from {before} to {len(service_posts)} using AI context words.")

    # 4. Deduplicate posts that match both search queries using their Bluesky URIs
    deduped: dict[str, dict[str, Any]] = {}
    add_posts(deduped, company_posts, company.company_query)
    add_posts(deduped, service_posts, company.service_query)

    # 5. Sort by engagement score (primary) and date (secondary, newest first)
    posts = list(deduped.values())
    posts.sort(key=lambda post: (post["engagement_score"], post.get("created_at") or ""), reverse=True)
    posts = posts[:keep_posts]

    # 6. Fetch top 3 direct thread replies for each retained post
    for post in posts:
        replies = get_top_direct_replies(post["uri"], limit=3)
        thread_calls += 1
        post["replies"] = replies

    reply_count = sum(len(post["replies"]) for post in posts)
    return {
        "company": company.label,
        "company_slug": company.slug,
        "ingested_at": iso_now(),
        "queries": {
            "company": company.company_query,
            "service": company.service_query,
        },
        "source": {
            "network": "Bluesky",
            "base_url": BLUESKY_BASE_URL,
            "search_endpoint": "app.bsky.feed.searchPosts",
            "thread_endpoint": "app.bsky.feed.getPostThread",
        },
        "api_calls": {
            "search": search_calls,
            "threads": thread_calls,
            "total": search_calls + thread_calls,
        },
        "post_count": len(posts),
        "reply_count": reply_count,
        "posts": posts,
        "notes": notes,
    }


def search_posts(query: str, *, limit: int) -> list[dict[str, Any]]:
    """Query the Bluesky search API for the top posts matching a query.

    Args:
        query: The search query string.
        limit: Max number of posts to return.

    Returns:
        A list of raw search post objects returned by the API.
    """
    payload = get_json(
        f"{BLUESKY_BASE_URL}/xrpc/app.bsky.feed.searchPosts",
        {"q": query, "sort": "top", "limit": limit},
    )
    return list(payload.get("posts") or [])


def add_posts(deduped: dict[str, dict[str, Any]], posts: list[dict[str, Any]], source_query: str) -> None:
    """Normalize and insert posts into a deduplication dictionary.

    If a post is already in the dictionary, appends the query to its source_queries
    list rather than overwriting it.

    Args:
        deduped: Dictionary mapping post URI keys to normalized post values.
        posts: List of raw search posts to insert.
        source_query: The query that fetched these posts.
    """
    for raw_post in posts:
        post = normalize_post(raw_post)
        if not post["uri"]:
            continue
        existing = deduped.get(post["uri"])
        if existing:
            existing["source_queries"].append(source_query)
            continue
        post["source_queries"] = [source_query]
        post["engagement_score"] = engagement_score(post)
        deduped[post["uri"]] = post


def get_top_direct_replies(uri: str, *, limit: int) -> list[dict[str, Any]]:
    """Fetch and filter the top direct replies for a given post URI.

    Queries the thread API, normalizes the replies, ensures they are direct replies,
    and returns them sorted by like count.

    Args:
        uri: The Bluesky URI of the root post.
        limit: The maximum number of replies to return.

    Returns:
        A list of normalized reply post dictionaries, sorted by like count.
    """
    payload = get_json(
        f"{BLUESKY_BASE_URL}/xrpc/app.bsky.feed.getPostThread",
        {"uri": uri, "depth": 1, "parentHeight": 0},
    )
    thread = payload.get("thread") or {}
    raw_replies = thread.get("replies") or []
    replies = []
    for raw_reply in raw_replies:
        raw_post = raw_reply.get("post") if isinstance(raw_reply, dict) else None
        if not raw_post:
            continue
        if is_direct_reply(raw_post, uri):
            replies.append(normalize_post(raw_post))
    # Sort replies by like count (primary) and date (secondary, newest first)
    replies.sort(key=lambda post: (int(post.get("like_count") or 0), post.get("created_at") or ""), reverse=True)
    return replies[:limit]


def is_direct_reply(raw_post: dict[str, Any], root_uri: str) -> bool:
    """Check if a post record is a direct reply to the root post URI.

    Args:
        raw_post: The raw post object containing the record dict.
        root_uri: The parent post URI we are checking against.

    Returns:
        True if the post is a direct child of root_uri, False otherwise.
    """
    record = raw_post.get("record") or {}
    reply = record.get("reply") or {}
    parent = reply.get("parent") or {}
    return parent.get("uri") == root_uri


def normalize_post(raw_post: dict[str, Any]) -> dict[str, Any]:
    """Map a raw Bluesky API post object into a simplified, flat schema.

    Args:
        raw_post: The complex raw post dictionary from the Bluesky API.

    Returns:
        A dictionary containing author info, text, timestamps, and interaction counts.
    """
    record = raw_post.get("record") or {}
    author = raw_post.get("author") or {}
    text = record.get("text") or ""
    normalized = {
        "uri": raw_post.get("uri"),
        "cid": raw_post.get("cid"),
        "text": text,
        "created_at": record.get("createdAt"),
        "indexed_at": raw_post.get("indexedAt"),
        "author": {
            "did": author.get("did"),
            "handle": author.get("handle"),
            "display_name": author.get("displayName"),
        },
        "like_count": int(raw_post.get("likeCount") or 0),
        "repost_count": int(raw_post.get("repostCount") or 0),
        "reply_count": int(raw_post.get("replyCount") or 0),
        "quote_count": int(raw_post.get("quoteCount") or 0),
    }
    normalized["engagement_score"] = engagement_score(normalized)
    return normalized


def is_ai_context_post(raw_post: dict[str, Any]) -> bool:
    """Evaluate if a post contains any AI-relevant keywords.

    Used to reduce non-AI noise for ambiguous terms like 'Gemini'.

    Args:
        raw_post: The raw post to evaluate.

    Returns:
        True if the post matches any keyword in GEMINI_AI_CONTEXT_WORDS, False otherwise.
    """
    record = raw_post.get("record") or {}
    text = (record.get("text") or "").lower()
    return any(word in text for word in GEMINI_AI_CONTEXT_WORDS)

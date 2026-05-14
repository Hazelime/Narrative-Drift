from __future__ import annotations

from typing import Any

from .config import BLUESKY_BASE_URL, CompanyConfig, GEMINI_AI_CONTEXT_WORDS
from .http import get_json
from .timeutil import iso_now


def engagement_score(post: dict[str, Any]) -> int:
    return (
        1 * int(post.get("like_count") or 0)
        + 3 * int(post.get("repost_count") or 0)
        + 4 * int(post.get("reply_count") or 0)
        + 5 * int(post.get("quote_count") or 0)
    )


def ingest_company(company: CompanyConfig, *, limit_per_query: int = 100, keep_posts: int = 50) -> dict[str, Any]:
    search_calls = 0
    thread_calls = 0
    notes: list[str] = []

    company_posts = search_posts(company.company_query, limit=limit_per_query)
    search_calls += 1

    service_posts = search_posts(company.service_query, limit=limit_per_query)
    search_calls += 1
    if company.service_query.lower() == "gemini":
        before = len(service_posts)
        service_posts = [post for post in service_posts if is_ai_context_post(post)]
        notes.append(f"Filtered Gemini service posts from {before} to {len(service_posts)} using AI context words.")

    deduped: dict[str, dict[str, Any]] = {}
    add_posts(deduped, company_posts, company.company_query)
    add_posts(deduped, service_posts, company.service_query)

    posts = list(deduped.values())
    posts.sort(key=lambda post: (post["engagement_score"], post.get("created_at") or ""), reverse=True)
    posts = posts[:keep_posts]

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
    payload = get_json(
        f"{BLUESKY_BASE_URL}/xrpc/app.bsky.feed.searchPosts",
        {"q": query, "sort": "top", "limit": limit},
    )
    return list(payload.get("posts") or [])


def add_posts(deduped: dict[str, dict[str, Any]], posts: list[dict[str, Any]], source_query: str) -> None:
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
    replies.sort(key=lambda post: (int(post.get("like_count") or 0), post.get("created_at") or ""), reverse=True)
    return replies[:limit]


def is_direct_reply(raw_post: dict[str, Any], root_uri: str) -> bool:
    record = raw_post.get("record") or {}
    reply = record.get("reply") or {}
    parent = reply.get("parent") or {}
    return parent.get("uri") == root_uri


def normalize_post(raw_post: dict[str, Any]) -> dict[str, Any]:
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
    record = raw_post.get("record") or {}
    text = (record.get("text") or "").lower()
    return any(word in text for word in GEMINI_AI_CONTEXT_WORDS)

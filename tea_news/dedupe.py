"""Hash-based dedup against a persisted sent-articles store."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from . import config

logger = logging.getLogger(__name__)


def hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def load_sent_store(path: str = config.SENT_ARTICLES_PATH) -> dict:
    if not os.path.exists(path):
        return {"sent": {}}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("sent_articles.json is not valid JSON; starting fresh")
            return {"sent": {}}
    data.setdefault("sent", {})
    return data


def save_sent_store(store: dict, path: str = config.SENT_ARTICLES_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def prune_old_entries(store: dict, retention_days: int = config.SENT_ARTICLES_RETENTION_DAYS) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    kept = {}
    for url_hash, entry in store.get("sent", {}).items():
        sent_at = entry.get("sent_at")
        try:
            sent_dt = datetime.fromisoformat(sent_at) if sent_at else None
        except ValueError:
            sent_dt = None
        if sent_dt is None or sent_dt >= cutoff:
            kept[url_hash] = entry
    store["sent"] = kept
    return store


def filter_new_articles(articles: list[dict], store: dict) -> list[dict]:
    """Return only articles whose URL hash is not already in the store, deduped
    against each other as well (Google News can return the same story from
    multiple regional queries)."""
    sent_hashes = set(store.get("sent", {}).keys())
    seen_in_batch = set()
    new_articles = []

    for article in articles:
        url_hash = hash_url(article["link"])
        if url_hash in sent_hashes or url_hash in seen_in_batch:
            continue
        seen_in_batch.add(url_hash)
        article["url_hash"] = url_hash
        new_articles.append(article)

    return new_articles


def mark_sent(articles: list[dict], store: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    for article in articles:
        store.setdefault("sent", {})[article["url_hash"]] = {
            "sent_at": now,
            "title": article["title"],
            "region": article["region_key"],
        }
    return store

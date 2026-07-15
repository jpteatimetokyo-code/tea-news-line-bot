"""RSS collection from Google News (per-region) and optional auxiliary feeds."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import feedparser
import requests

from . import config

logger = logging.getLogger(__name__)


def _build_google_news_url(region: dict) -> str:
    query_string = urlencode(
        {
            "q": region["query"],
            "hl": region["hl"],
            "gl": region["gl"],
            "ceid": f"{region['gl']}:{region['hl']}",
        }
    )
    return f"{config.GOOGLE_NEWS_RSS_BASE}?{query_string}"


def _fetch_feed_entries(url: str) -> list:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch feed %s: %s", url, exc)
        return []

    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        logger.warning("Feed at %s could not be parsed: %s", url, parsed.bozo_exception)
        return []
    return parsed.entries


def collect_region(region: dict, max_per_region: int | None = None) -> list[dict]:
    """Fetch and normalize articles for a single region."""
    url = _build_google_news_url(region)
    entries = _fetch_feed_entries(url)

    articles = []
    for entry in entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue

        source_title = ""
        source = entry.get("source")
        if isinstance(source, dict):
            source_title = source.get("title", "")

        articles.append(
            {
                "title": title,
                "link": link,
                "published": entry.get("published", ""),
                "snippet": entry.get("summary", ""),
                "source": source_title,
                "region_key": region["key"],
                "region_label": region["label"],
                "region_priority": region["priority"],
            }
        )
        if max_per_region and len(articles) >= max_per_region:
            break

    logger.info("Collected %d articles for region %s", len(articles), region["key"])
    return articles


def collect_auxiliary(source: dict, max_articles: int | None = None) -> list[dict]:
    """Fetch and normalize articles from a non-Google-News RSS source."""
    entries = _fetch_feed_entries(source["rss_url"])

    articles = []
    for entry in entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue

        articles.append(
            {
                "title": title,
                "link": link,
                "published": entry.get("published", ""),
                "snippet": entry.get("summary", ""),
                "source": source["label"],
                "region_key": source["key"],
                "region_label": source["label"],
                "region_priority": source["priority"],
            }
        )
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Collected %d articles from auxiliary source %s", len(articles), source["key"])
    return articles


def collect_all(max_per_region: int | None = None) -> list[dict]:
    """Collect articles from every configured region (and auxiliary sources)."""
    all_articles: list[dict] = []

    for region in config.REGIONS:
        all_articles.extend(collect_region(region, max_per_region=max_per_region))

    if config.AUXILIARY_SOURCES_ENABLED:
        for source in config.AUXILIARY_SOURCES:
            all_articles.extend(collect_auxiliary(source, max_articles=max_per_region))

    return all_articles

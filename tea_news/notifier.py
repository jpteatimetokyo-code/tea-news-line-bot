"""Build the LINE message text and push it via the Messaging API."""

from __future__ import annotations

import datetime
import logging
import os

import requests

from . import config

logger = logging.getLogger(__name__)


def order_articles(articles: list[dict]) -> list[dict]:
    """Sort by region priority (ascending = higher precedence), preserving the
    order articles were collected in within a region."""
    return sorted(articles, key=lambda a: a["region_priority"])


def build_message_text(articles: list[dict]) -> str:
    today = datetime.date.today().isoformat()
    lines = [f"🍵 世界の茶ニュース ({today})", ""]

    current_region = None
    for article in order_articles(articles):
        if article["region_label"] != current_region:
            current_region = article["region_label"]
            lines.append(f"■ {current_region}")

        lines.append(f"・{article['headline_ja']}")
        lines.append(article["summary_ja"])
        lines.append(article["link"])
        lines.append("")

    if len(lines) == 2:
        lines.append("本日は新着記事がありませんでした。")

    return "\n".join(lines).strip()


def chunk_message(text: str, max_chars: int = config.LINE_MAX_MESSAGE_CHARS) -> list[str]:
    """Split text into chunks under max_chars, breaking on blank lines where
    possible so an article block is never split mid-way."""
    if len(text) <= max_chars:
        return [text]

    blocks = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = block
        else:
            current = candidate

        # A single block longer than max_chars must be hard-split.
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]

    if current:
        chunks.append(current)

    return chunks


def send_line_push(chunks: list[str], dry_run: bool = False) -> None:
    if not chunks:
        logger.info("No message content to send.")
        return

    if dry_run:
        print("=== DRY RUN: LINE message(s) that would be sent ===")
        for i, chunk in enumerate(chunks, start=1):
            print(f"--- message {i}/{len(chunks)} ({len(chunk)} chars) ---")
            print(chunk)
        print("=== END DRY RUN ===")
        return

    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "LINE_CHANNEL_ACCESS_TOKEN and LINE_USER_ID must be set to send a "
            "real LINE message. Use --dry-run to test without them."
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    for start in range(0, len(chunks), config.LINE_MAX_MESSAGES_PER_PUSH):
        group = chunks[start : start + config.LINE_MAX_MESSAGES_PER_PUSH]
        payload = {
            "to": user_id,
            "messages": [{"type": "text", "text": chunk} for chunk in group],
        }
        response = requests.post(
            config.LINE_PUSH_URL,
            headers=headers,
            json=payload,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            logger.error("LINE push failed (%d): %s", response.status_code, response.text)
            response.raise_for_status()
        logger.info("Sent %d message(s) to LINE.", len(group))

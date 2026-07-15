#!/usr/bin/env python3
"""Daily tea-news collector: RSS収集 → 重複排除 → 翻訳要約 → LINE送信。

Usage:
    python main.py                  # real run: sends to LINE, updates sent_articles.json
    python main.py --dry-run        # local test: prints the message, does not send or persist
    python main.py --dry-run --no-translate --max-per-region 2   # fast, no API calls at all
"""

from __future__ import annotations

import argparse
import logging
import sys

from tea_news import collector, dedupe, notifier, summarizer
from tea_news.config import DEFAULT_MAX_ARTICLES_PER_RUN, DEFAULT_MAX_PER_REGION


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the LINE message instead of sending it, and do not update sent_articles.json.",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip the Claude API call; use raw titles instead of translated summaries. "
        "Useful for testing the collection/dedup/LINE-formatting pipeline without an API key.",
    )
    parser.add_argument(
        "--max-per-region",
        type=int,
        default=DEFAULT_MAX_PER_REGION,
        help=f"Max articles to keep per region feed (default: {DEFAULT_MAX_PER_REGION}).",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=DEFAULT_MAX_ARTICLES_PER_RUN,
        help=f"Max total new articles to translate/send per run (default: {DEFAULT_MAX_ARTICLES_PER_RUN}).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the Claude model ID (default: env CLAUDE_MODEL or claude-opus-4-8).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("main")

    logger.info("Collecting RSS feeds...")
    raw_articles = collector.collect_all(max_per_region=args.max_per_region)
    logger.info("Collected %d raw articles across all regions.", len(raw_articles))

    store = dedupe.load_sent_store()
    new_articles = dedupe.filter_new_articles(raw_articles, store)
    logger.info("%d new (unsent) articles after dedup.", len(new_articles))

    new_articles = notifier.order_articles(new_articles)[: args.max_articles]
    if not new_articles:
        logger.info("Nothing new to send today.")

    logger.info("Translating/summarizing %d article(s)...", len(new_articles))
    enriched_articles = summarizer.translate_articles(
        new_articles, no_translate=args.no_translate, model=args.model
    )

    message_text = notifier.build_message_text(enriched_articles)
    chunks = notifier.chunk_message(message_text)
    logger.info("Built %d LINE message chunk(s).", len(chunks))

    notifier.send_line_push(chunks, dry_run=args.dry_run)

    if not args.dry_run and enriched_articles:
        store = dedupe.mark_sent(enriched_articles, store)
        store = dedupe.prune_old_entries(store)
        dedupe.save_sent_store(store)
        logger.info("Updated sent_articles.json with %d new entries.", len(enriched_articles))
    elif args.dry_run:
        logger.info("Dry run: sent_articles.json was not modified.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

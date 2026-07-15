"""Translate and summarize articles into Japanese via the Claude API."""

from __future__ import annotations

import html
import json
import logging
import os
import re

import anthropic

from . import config

logger = logging.getLogger(__name__)

BATCH_SIZE = 15

SYSTEM_PROMPT = """\
あなたは世界の茶(お茶)ニュースを日本の読者向けに翻訳・要約するアシスタントです。
入力される各記事(タイトルと取得できた範囲の本文/概要、および地域ラベル)について、
以下を生成してください。

- headline_ja: 日本語の見出し。1行、40文字程度まで。
- summary_ja: 3〜4行程度の日本語要約。記事の要点(何が起きたか、なぜ重要か)を
  簡潔にまとめる。元記事が英語・中国語・ドイツ語など他言語であっても、
  必ず自然な日本語に翻訳・要約すること。
- 日本茶・抹茶・煎茶に関する記事は特に丁寧に、各国の茶文化全般の記事も
  同様に要約すること。
- 記事本文の情報が乏しい場合でも、タイトルや概要から推測できる範囲で
  簡潔な要約を作ること。
"""


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _build_batch_prompt(articles: list[dict]) -> str:
    items = []
    for i, article in enumerate(articles):
        items.append(
            {
                "id": i,
                "region": article["region_label"],
                "title": article["title"],
                "snippet": _strip_html(article.get("snippet", ""))[:800],
            }
        )
    return json.dumps({"articles": items}, ensure_ascii=False)


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "headline_ja": {"type": "string"},
                    "summary_ja": {"type": "string"},
                },
                "required": ["id", "headline_ja", "summary_ja"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["articles"],
    "additionalProperties": False,
}


def _translate_batch(client: anthropic.Anthropic, model: str, articles: list[dict]) -> dict[int, dict]:
    user_content = (
        "以下はJSON形式の記事リストです。各記事について headline_ja と summary_ja を"
        "生成し、指定されたスキーマのJSONで返してください。\n\n"
        + _build_batch_prompt(articles)
    )

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
    )

    text = next((block.text for block in response.content if block.type == "text"), "")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response as JSON: %s", text[:500])
        return {}

    return {item["id"]: item for item in parsed.get("articles", [])}


def translate_articles(
    articles: list[dict],
    no_translate: bool = False,
    model: str | None = None,
) -> list[dict]:
    """Attach headline_ja / summary_ja to each article dict, in place-compatible
    fashion (returns a new list of enriched dicts)."""
    if not articles:
        return []

    if no_translate:
        enriched = []
        for article in articles:
            enriched.append(
                {
                    **article,
                    "headline_ja": article["title"],
                    "summary_ja": "(--no-translate: 要約はスキップされました)",
                }
            )
        return enriched

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it in the environment, or pass "
            "--no-translate for a translation-free local test run."
        )

    client = anthropic.Anthropic(api_key=api_key)
    model = model or os.environ.get("CLAUDE_MODEL", config.DEFAULT_MODEL)

    enriched: list[dict] = []
    for start in range(0, len(articles), BATCH_SIZE):
        batch = articles[start : start + BATCH_SIZE]
        logger.info("Translating batch %d-%d of %d", start, start + len(batch), len(articles))
        results = _translate_batch(client, model, batch)

        for i, article in enumerate(batch):
            result = results.get(i)
            if result:
                enriched.append(
                    {
                        **article,
                        "headline_ja": result["headline_ja"],
                        "summary_ja": result["summary_ja"],
                    }
                )
            else:
                logger.warning("No translation result for article: %s", article["title"])
                enriched.append(
                    {
                        **article,
                        "headline_ja": article["title"],
                        "summary_ja": "(翻訳に失敗しました)",
                    }
                )

    return enriched

# 世界の茶ニュース 日本語LINE配信システム

世界各国の茶(お茶)関連ニュースを毎日自動収集し、日本語に翻訳・要約したうえで LINE に通知するボットです。

- **収集**: 地域・言語ごとの Google News RSS
- **重複排除**: 記事URLのハッシュを `sent_articles.json` に永続化
- **翻訳・要約**: Anthropic Claude API (`claude-opus-4-8`)
- **配信**: LINE Messaging API (push message)
- **実行**: GitHub Actions で毎日自動実行(自分のPCの起動は不要)

対象地域は「日本茶の味・文化が受け入れられやすい順」で優先度付けされており、
LINEメッセージ内でもその順に記事が並びます: 中華圏(台湾・香港・中国)→ドイツ→
フランス→シンガポール→タイ→ベトナム→中東→アメリカ。

## ディレクトリ構成

```
tea-news-line-bot/
├── main.py                    # エントリーポイント
├── tea_news/
│   ├── config.py               # 地域・クエリ・各種定数
│   ├── collector.py            # RSS収集
│   ├── dedupe.py               # 重複排除(sent_articles.json)
│   ├── summarizer.py           # Claude APIによる翻訳・要約
│   └── notifier.py             # LINE Messaging APIへの送信
├── sent_articles.json          # 送信済み記事のハッシュ(自動更新・コミットされる)
├── requirements.txt
├── .env.example
└── .github/workflows/daily.yml # 毎日実行するworkflow
```

## セットアップ

### 1. LINE Messaging API の準備(手動作業)

LINE Notify は2025年3月31日に終了したため、後継の **LINE Messaging API** を使用します。

1. [LINE Developers](https://developers.line.biz/) で LINE公式アカウントを作成(無料)
2. 作成したチャネルで **Messaging API** を有効化
3. 「Messaging API設定」タブから **チャネルアクセストークン(長期)** を発行
4. 自分の **ユーザーID** を取得(LINE Developersコンソールの「基本設定」タブの
   「あなたのユーザーID」、または Webhook 経由で取得)
5. 作成した公式アカウントを自分のLINEアプリで **友だち追加**(QRコードはコンソールから確認可能)

### 2. Anthropic API キーの取得

[Anthropic Console](https://console.anthropic.com/) で API キーを発行してください。

### 3. GitHub Secrets の設定

このリポジトリの GitHub 上で **Settings → Secrets and variables → Actions → New repository secret**
から以下を登録してください:

| Secret名 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API キー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API のチャネルアクセストークン |
| `LINE_USER_ID` | 通知を受け取る自分のLINEユーザーID |

Secrets を設定すれば、`.github/workflows/daily.yml` が毎日自動実行され、
自分のPCを起動しておく必要はありません(手動実行は Actions タブの
「Run workflow」からも可能)。

### 4. ローカルでのセットアップ(テスト用)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env を編集してAPIキー等を入力

set -a; source .env; set +a
```

## ローカルテスト実行(dry-run)

`--dry-run` を付けると、LINEへの実送信も `sent_articles.json` の更新も行わず、
生成されるメッセージを標準出力に表示するだけになります。何度でも安全に再実行できます。

```bash
# フル機能(Claude APIで翻訳、LINEには送らない)
python main.py --dry-run

# 各地域2記事までに絞って高速テスト
python main.py --dry-run --max-per-region 2

# Claude APIキーなしでもパイプライン全体(収集・重複排除・整形)を確認したい場合
python main.py --dry-run --no-translate --max-per-region 2
```

本番実行(LINEに実際に送信し、`sent_articles.json` を更新)は引数なしで実行します:

```bash
python main.py
```

### 主なオプション

| オプション | 説明 |
|---|---|
| `--dry-run` | LINE送信と `sent_articles.json` の更新をスキップし、内容を表示するだけ |
| `--no-translate` | Claude API呼び出しをスキップし、原題をそのまま使う(APIキー不要のテスト用) |
| `--max-per-region N` | 地域ごとに保持する記事数の上限(デフォルト: 8) |
| `--max-articles N` | 1回の実行で翻訳・送信する記事数の上限(デフォルト: 40) |
| `--model MODEL_ID` | 使用するClaudeモデルを上書き(デフォルト: `claude-opus-4-8`、環境変数`CLAUDE_MODEL`でも指定可) |
| `-v`, `--verbose` | デバッグログを表示 |

## 実行スケジュール

`.github/workflows/daily.yml` は毎日 **UTC 22:00 (= JST 07:00 翌日)** に実行されます。
GitHub Actions の `cron` は常にUTCなので、時刻を変更する場合は
`JST時刻 - 9時間` を計算してcron式に反映してください(日付をまたぐ場合に注意)。

## 重複排除の仕組み

各記事のURLをSHA-256でハッシュ化し、`sent_articles.json` に `{"sent": {"<hash>": {...}}}`
の形で保存します。GitHub Actions実行後、変更があれば自動的にこのファイルを
リポジトリへコミット・プッシュするため、実行間で送信済み状態が維持されます
(60日より古いエントリは自動的に整理されます)。

## 補助ソース(World Tea News)について

仕様では英語の業界メディア World Tea News (worldteanews.com) を補助ソースとして
利用する案がありましたが、実装時点で `https://www.worldteanews.com/feed` は
HTTP 404 を返しており、RSS配信が終了(または変更)している状態を確認しました。
そのため `tea_news/config.py` の `AUXILIARY_SOURCES_ENABLED = False` により
デフォルトでは無効化しています。有効なフィードURLが見つかった場合は
`AUXILIARY_SOURCES` にURLを設定し `AUXILIARY_SOURCES_ENABLED = True` にすることで
再度有効化できます。

## カスタマイズ

- 対象地域・検索クエリ: `tea_news/config.py` の `REGIONS`
- 1メッセージあたりの文字数上限やLINE API URL: `tea_news/config.py`
- 翻訳・要約のプロンプト: `tea_news/summarizer.py` の `SYSTEM_PROMPT`
- 使用モデル: 環境変数 `CLAUDE_MODEL`、または `--model` オプション
  (デフォルトは `claude-opus-4-8`。コストを抑えたい場合は `claude-sonnet-5` や
  `claude-haiku-4-5` などに変更可能)

"""Region and query configuration for tea news collection.

Priority order follows the spec: regions where Japanese tea culture is most
readily received come first (lower ``priority`` = higher precedence in the
final LINE message).
"""

# Each region defines a Google News RSS query.
# URL shape: https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={gl}:{hl}
REGIONS = [
    {
        "key": "zh-tw",
        "label": "台湾",
        "hl": "zh-TW",
        "gl": "TW",
        "query": "日本茶 OR 抹茶 OR 煎茶",
        "priority": 1,
    },
    {
        "key": "zh-hk",
        "label": "香港",
        "hl": "zh-HK",
        "gl": "HK",
        "query": "日本茶 OR 抹茶 OR 煎茶",
        "priority": 1,
    },
    {
        "key": "zh-cn",
        "label": "中国",
        "hl": "zh-CN",
        "gl": "CN",
        "query": "日本茶 OR 抹茶",
        "priority": 1,
    },
    {
        "key": "de",
        "label": "ドイツ",
        "hl": "de",
        "gl": "DE",
        "query": "japanischer Tee OR Matcha",
        "priority": 2,
    },
    {
        "key": "fr",
        "label": "フランス",
        "hl": "fr",
        "gl": "FR",
        "query": "thé japonais OR matcha",
        "priority": 3,
    },
    {
        "key": "sg",
        "label": "シンガポール",
        "hl": "en-SG",
        "gl": "SG",
        "query": "Japanese tea OR matcha",
        "priority": 4,
    },
    {
        "key": "th",
        "label": "タイ",
        "hl": "th",
        "gl": "TH",
        "query": "ชาญี่ปุ่น OR มัทชะ",
        "priority": 5,
    },
    {
        "key": "vn",
        "label": "ベトナム",
        "hl": "vi",
        "gl": "VN",
        "query": "trà Nhật Bản OR matcha",
        "priority": 6,
    },
    {
        "key": "me",
        "label": "中東",
        "hl": "ar",
        "gl": "AE",
        "query": "الشاي الياباني OR matcha",
        "priority": 7,
    },
    {
        "key": "us",
        "label": "アメリカ",
        "hl": "en-US",
        "gl": "US",
        "query": "Japanese tea OR matcha OR sencha",
        "priority": 8,
    },
]

# World Tea News (worldteanews.com) was listed in the spec as an optional
# auxiliary English-language industry source. As of this implementation its
# RSS feed (https://www.worldteanews.com/feed) returns HTTP 404 -- the feed
# appears discontinued. It is disabled by default; flip AUXILIARY_SOURCES_ENABLED
# to True and fill in a working feed URL below if that changes.
AUXILIARY_SOURCES_ENABLED = False
AUXILIARY_SOURCES = [
    {
        "key": "worldteanews",
        "label": "業界メディア",
        "rss_url": "https://www.worldteanews.com/feed",
        "priority": 9,
    },
]

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"

DEFAULT_MODEL = "claude-opus-4-8"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_MAX_MESSAGE_CHARS = 4800  # stay under the 5000-char LINE limit with margin
LINE_MAX_MESSAGES_PER_PUSH = 5  # LINE push API accepts up to 5 messages per call

SENT_ARTICLES_PATH = "sent_articles.json"
SENT_ARTICLES_RETENTION_DAYS = 60

DEFAULT_MAX_ARTICLES_PER_RUN = 40
DEFAULT_MAX_PER_REGION = 8

REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

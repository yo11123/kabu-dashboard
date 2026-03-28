"""
市場ニュース取得モジュール

Google News RSS から株式市場に影響する最新ニュースをカテゴリ別に取得する。
views/news.py（ニュースページ）と views/buy_timing.py（買い時スクリーナー）で共用。
"""

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st


# ─── カテゴリ定義 ────────────────────────────────────────────────────────

NEWS_CATEGORIES: list[dict] = [
    {
        "name": "日本株・マーケット",
        "queries": [
            "日経平均 株価 マーケット",
            "東証 株式市場 相場",
        ],
    },
    {
        "name": "米国株・グローバル",
        "queries": [
            "米国株 S&P ナスダック ダウ",
            "米FRB 金利 利下げ 利上げ",
        ],
    },
    {
        "name": "為替・金利",
        "queries": [
            "ドル円 為替 円安 円高",
            "日本銀行 金融政策 金利",
        ],
    },
    {
        "name": "地政学・国際情勢",
        "queries": [
            "地政学リスク 戦争 紛争 制裁",
            "米中 貿易摩擦 関税",
            "イラン イスラエル フーシ派 中東",
            "ウクライナ ロシア NATO 軍事",
            "北朝鮮 台湾 安全保障",
        ],
    },
    {
        "name": "コモディティ・エネルギー",
        "queries": [
            "原油 金 価格 商品",
            "エネルギー 資源 供給",
        ],
    },
    {
        "name": "企業・決算",
        "queries": [
            "企業決算 業績 上方修正 下方修正",
            "M&A 買収 上場 IPO",
        ],
    },
    {
        "name": "経済指標・マクロ",
        "queries": [
            "GDP CPI 雇用統計 経済指標",
            "景気 インフレ デフレ 経済",
        ],
    },
    {
        "name": "テクノロジー・AI",
        "queries": [
            "AI 半導体 テクノロジー 株",
            "NVIDIA OpenAI テック 投資",
        ],
    },
]


# ─── ニュース取得 ────────────────────────────────────────────────────────


def fetch_rss(query: str, max_items: int = 15) -> list[dict]:
    """Google News RSS から記事を取得する（1週間以内のみ）。"""
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    try:
        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}+when:7d&hl=ja&gl=JP&ceid=JP:ja"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; kabu-dashboard/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items: list[dict] = []

        for item_el in root.findall(".//item"):
            title = item_el.findtext("title", "").strip()
            link = item_el.findtext("link", "").strip()
            pub_date_str = item_el.findtext("pubDate", "")
            source_el = item_el.find("source")
            publisher = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else ""
            )

            if not title or not pub_date_str:
                continue

            if publisher:
                suffix = f" - {publisher}"
                if title.endswith(suffix):
                    title = title[: -len(suffix)].strip()

            try:
                pub_dt = pd.Timestamp(pub_date_str)
                if pub_dt.tz is not None:
                    pub_dt = pub_dt.tz_convert("Asia/Tokyo").tz_localize(None)
            except Exception:
                continue

            if pub_dt < cutoff:
                continue

            items.append({
                "pub_dt": pub_dt,
                "title": title,
                "publisher": publisher,
                "link": link,
            })

        items.sort(key=lambda x: x["pub_dt"], reverse=True)
        return items[:max_items]
    except Exception:
        return []


# ─── 類似記事除去 ────────────────────────────────────────────────────────


def _tokenize(title: str) -> set[str]:
    """タイトルを簡易トークン化する。"""
    tokens = re.split(r'[\s,、。・/\-\|「」『』（）()【】\[\]：:]+', title)
    stop = {"の", "は", "が", "を", "に", "で", "と", "も", "へ", "や", "か", "な",
            "だ", "た", "て", "する", "した", "から", "まで", "より", "など",
            "ら", "れ", "さ", "し", "い", "る", "ない", "ある", "いる",
            "the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "on"}
    return {t.lower() for t in tokens if len(t) > 1 and t.lower() not in stop}


def _similarity(a: set[str], b: set[str]) -> float:
    """2つのトークン集合のJaccard類似度を返す。"""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_PUBLISHER_PRIORITY = {
    "日本経済新聞": 0, "日経": 0, "ロイター": 1, "Reuters": 1,
    "Bloomberg": 2, "ブルームバーグ": 2, "株探": 3, "東洋経済": 4,
    "NHK": 2, "朝日新聞": 3, "読売新聞": 3, "毎日新聞": 3,
}


def dedup_similar(items: list[dict], threshold: float = 0.45) -> list[dict]:
    """類似ニュースをグループ化し、各グループから最も詳しい記事のみ残す。"""
    def _priority(item: dict) -> int:
        pub = item.get("publisher", "")
        for name, pri in _PUBLISHER_PRIORITY.items():
            if name in pub:
                return pri
        return 9

    if not items:
        return []

    tokenized = [(item, _tokenize(item["title"])) for item in items]
    groups: list[list[int]] = []
    assigned: set[int] = set()

    for i, (_, tokens_i) in enumerate(tokenized):
        if i in assigned:
            continue
        group = [i]
        assigned.add(i)
        for j, (_, tokens_j) in enumerate(tokenized):
            if j in assigned:
                continue
            if _similarity(tokens_i, tokens_j) >= threshold:
                group.append(j)
                assigned.add(j)
        groups.append(group)

    result: list[dict] = []
    for group in groups:
        candidates = [items[idx] for idx in group]
        candidates.sort(key=lambda x: (-len(x["title"]), _priority(x)))
        result.append(candidates[0])
    return result


# ─── カテゴリ別・全件取得 ────────────────────────────────────────────────


@st.cache_data(ttl=600, show_spinner=False)
def fetch_category_news(queries: tuple[str, ...], max_items: int = 20) -> list[dict]:
    """カテゴリ内の全クエリからニュースを取得しマージ・類似記事を除去する。"""
    all_items: list[dict] = []
    for q in queries:
        all_items.extend(fetch_rss(q, max_items=15))

    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_items:
        key = item["title"][:35]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    deduped = dedup_similar(unique)
    deduped.sort(key=lambda x: x["pub_dt"], reverse=True)
    return deduped[:max_items]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_news() -> dict[str, list[dict]]:
    """全カテゴリのニュースを一括取得する。"""
    result: dict[str, list[dict]] = {}
    for cat in NEWS_CATEGORIES:
        items = fetch_category_news(tuple(cat["queries"]), max_items=20)
        result[cat["name"]] = items
    return result


def format_news_for_prompt(all_news: dict[str, list[dict]] | None = None,
                           max_per_cat: int = 8) -> str:
    """AI分析プロンプト用にニュースをカテゴリ別テキストに整形する。"""
    if all_news is None:
        all_news = fetch_all_news()

    sections: list[str] = []
    for cat in NEWS_CATEGORIES:
        items = all_news.get(cat["name"], [])
        if not items:
            continue
        titles = "\n".join(f"- {it['title']}" for it in items[:max_per_cat])
        sections.append(f"### {cat['name']}\n{titles}")

    if not sections:
        return ""

    return "## 最新の市場ニュース（直近1週間・カテゴリ別）\n\n" + "\n\n".join(sections)

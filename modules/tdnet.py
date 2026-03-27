"""
TDNet（適時開示情報）から IR 開示情報を取得するモジュール。

東証の適時開示システム (TDNet) のページをスクレイピングし、
各開示の種別・インパクトを判定して返す。
"""

import re
from datetime import datetime

import requests
import pandas as pd
import streamlit as st
from lxml import html as lhtml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TDNET_URL = "https://www.release.tdnet.info/inbs/I_list_001_{code4}.html"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# カテゴリ判定ルール (順序が重要 — 先にマッチしたものが優先)
# ---------------------------------------------------------------------------

_CATEGORY_RULES: list[tuple[str, str, str]] = [
    # (正規表現パターン, カテゴリ名, インパクト)
    (r"自己株式の取得",           "自己株取得",   "positive"),
    (r"配当予想の修正.*増配|増配", "増配",         "positive"),
    (r"配当予想の修正.*減配|減配", "減配",         "negative"),
    (r"業績予想の修正.*上方",     "上方修正",     "positive"),
    (r"業績予想の修正.*下方",     "下方修正",     "negative"),
    (r"MBO|公開買付",            "MBO/TOB",      "positive"),
    (r"株式分割",                "株式分割",     "positive"),
    (r"新株予約権|第三者割当",    "希薄化",       "negative"),
    (r"代表取締役の異動",        "経営陣変更",   "neutral"),
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def categorize_disclosure(title: str) -> tuple[str, str]:
    """開示タイトルからカテゴリとインパクトを判定する。

    Returns:
        (category, impact) — impact は "positive" / "negative" / "neutral"
    """
    for pattern, category, impact in _CATEGORY_RULES:
        if re.search(pattern, title):
            return category, impact
    return "その他IR", "neutral"


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tdnet_disclosures(ticker: str) -> list[dict]:
    """単一銘柄の TDNet 適時開示情報を取得する。

    Args:
        ticker: 日本株ティッカー（例: "7203.T" or "7203"）

    Returns:
        開示情報の辞書リスト。各辞書のキー:
        date, title, category, impact, link, code
    """
    # 4桁コードを抽出
    code4 = re.sub(r"\D", "", str(ticker))[:4]
    if len(code4) < 4:
        return []

    url = TDNET_URL.format(code4=code4)

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    # エンコーディング処理
    resp.encoding = resp.apparent_encoding or "utf-8"
    tree = lhtml.fromstring(resp.text)

    disclosures: list[dict] = []

    # TDNet のページはテーブル行に開示情報が並ぶ
    # 一般的な構造: <table> 内の各 <tr> に日時・コード・社名・タイトル・PDF
    rows = tree.xpath("//table//tr")

    for row in rows:
        cells = row.xpath(".//td")
        if len(cells) < 4:
            continue

        # 各セルからテキストを取得
        date_text = cells[0].text_content().strip()
        code_text = cells[1].text_content().strip()
        # cells[2] は会社名
        title_text = cells[3].text_content().strip()

        if not title_text or not date_text:
            continue

        # コードが対象銘柄か確認（ページに複数銘柄が混在する場合）
        row_code = re.sub(r"\D", "", code_text)[:4]
        if row_code and row_code != code4:
            continue

        # リンクを取得
        link_el = cells[3].xpath(".//a/@href")
        if link_el:
            link = link_el[0]
            if link.startswith("/"):
                link = "https://www.release.tdnet.info" + link
        else:
            link = ""

        # 日付パース（"2026/03/27 15:00" 等）
        parsed_date = _parse_date(date_text)

        category, impact = categorize_disclosure(title_text)

        disclosures.append(
            {
                "date": parsed_date,
                "title": title_text,
                "category": category,
                "impact": impact,
                "link": link,
                "code": code4,
            }
        )

    return disclosures


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tdnet_recent(tickers: tuple[str, ...]) -> list[dict]:
    """複数銘柄の TDNet 適時開示情報をまとめて取得する。

    Args:
        tickers: ティッカーのタプル（例: ("7203.T", "6758.T")）
            ※ st.cache_data の hashability のため tuple を使用

    Returns:
        全銘柄分の開示情報を日付降順でソートしたリスト
    """
    all_disclosures: list[dict] = []
    for ticker in tickers:
        items = fetch_tdnet_disclosures(ticker)
        all_disclosures.extend(items)

    # 日付降順ソート
    all_disclosures.sort(key=lambda x: x.get("date", ""), reverse=True)
    return all_disclosures


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_date(date_text: str) -> str:
    """日付文字列をパースして ISO 形式 (YYYY-MM-DD) に変換する。"""
    # よくある形式を試す
    for fmt in (
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日 %H:%M",
        "%Y年%m月%d日",
    ):
        try:
            dt = datetime.strptime(date_text.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # パース失敗時は元のテキストをそのまま返す
    return date_text.strip()

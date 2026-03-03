"""
信用残高・貸借倍率データを取得するモジュール。

データソース優先順位:
  1. J-Quants API（JQUANTS_REFRESH_TOKEN が設定されている場合）
  2. Kabutan スクレイピング（フォールバック）
"""

import re

import requests
import streamlit as st
from lxml import html as lhtml


def _parse_number(text: str) -> float | None:
    """'1,234,567' や '1.23' などの数値文字列を float に変換する。"""
    text = re.sub(r"[,，千株万単位\s]", "", text.strip())
    try:
        return float(text)
    except ValueError:
        return None


def _scrape_kabutan(code4: str) -> dict:
    """Kabutan の信用残ページからデータをスクレイピングする。"""
    url = f"https://kabutan.jp/stock/merit?code={code4}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tree = lhtml.fromstring(resp.content)

    result: dict = {}

    # --- 貸借倍率テーブルを探す ---
    # 「貸借倍率」を含むテーブルを検索
    tables = tree.xpath("//table[.//*[contains(text(),'貸借倍率') or contains(text(),'信用買')]]")
    for table in tables:
        rows = table.xpath(".//tr")
        for row in rows:
            cells = row.xpath(".//th|.//td")
            texts = [c.text_content().strip() for c in cells]
            for i, t in enumerate(texts):
                if ("信用買い残" in t or "買い残" in t) and i + 1 < len(texts):
                    v = _parse_number(texts[i + 1])
                    if v is not None:
                        result["buy_margin"] = v
                if ("信用売り残" in t or "売り残" in t) and i + 1 < len(texts):
                    v = _parse_number(texts[i + 1])
                    if v is not None:
                        result["sell_margin"] = v
                if "貸借倍率" in t and i + 1 < len(texts):
                    v = _parse_number(texts[i + 1])
                    if v is not None:
                        result["lending_ratio"] = v

    # --- 表形式（ヘッダー行 + データ行）のパターンにも対応 ---
    if not result:
        headers_found = tree.xpath(
            "//th[contains(text(),'貸借倍率')]"
            "| //td[contains(@class,'credit') and contains(text(),'貸借倍率')]"
        )
        for h in headers_found:
            parent_row = h.getparent()
            if parent_row is None:
                continue
            parent_table = parent_row.getparent()
            if parent_table is None:
                continue
            data_rows = parent_table.xpath(".//tbody/tr")
            if not data_rows:
                data_rows = parent_table.xpath(".//tr")[1:]
            if data_rows:
                cells = data_rows[0].xpath(".//td")
                all_headers = parent_row.xpath(".//th|.//td")
                header_texts = [c.text_content().strip() for c in all_headers]
                cell_texts = [c.text_content().strip() for c in cells]
                for j, ht in enumerate(header_texts):
                    if j < len(cell_texts):
                        if "買い残" in ht:
                            v = _parse_number(cell_texts[j])
                            if v:
                                result["buy_margin"] = v
                        elif "売り残" in ht:
                            v = _parse_number(cell_texts[j])
                            if v:
                                result["sell_margin"] = v
                        elif "貸借倍率" in ht:
                            v = _parse_number(cell_texts[j])
                            if v:
                                result["lending_ratio"] = v

    # 貸借倍率が未取得でも買い・売り残があれば計算
    if (
        "lending_ratio" not in result
        and result.get("buy_margin")
        and result.get("sell_margin")
        and result["sell_margin"] > 0
    ):
        result["lending_ratio"] = round(
            result["buy_margin"] / result["sell_margin"], 2
        )

    return result


def _fetch_jquants_margin(code4: str, refresh_token: str) -> dict:
    """J-Quants API から信用残データを取得する（オプション）。"""
    # アクセストークン取得
    resp = requests.post(
        "https://api.jquants.com/v1/token/auth_refresh",
        params={"refreshtoken": refresh_token},
        timeout=10,
    )
    resp.raise_for_status()
    access_token = resp.json()["idToken"]

    # 5桁コードに変換（J-Quants は "72030" 形式）
    code5 = code4.zfill(4) + "0"

    resp = requests.get(
        "https://api.jquants.com/v1/markets/weekly_margin_interest",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"code": code5},
        timeout=15,
    )
    resp.raise_for_status()
    records = resp.json().get("weekly_margin_interest", [])
    if not records:
        return {}

    # 最新データを取得
    latest = sorted(records, key=lambda x: x.get("Date", ""), reverse=True)[0]
    buy  = latest.get("LongMarginTradeVolume")
    sell = latest.get("ShortMarginTradeVolume")
    result: dict = {}
    if buy is not None:
        result["buy_margin"] = float(buy)
    if sell is not None:
        result["sell_margin"] = float(sell)
    if buy and sell and float(sell) > 0:
        result["lending_ratio"] = round(float(buy) / float(sell), 2)
    result["date"] = latest.get("Date", "")
    return result


@st.cache_data(ttl=3600 * 6)  # 信用残は週次更新なので6時間キャッシュ
def fetch_margin_data(ticker: str) -> dict:
    """
    信用残高・貸借倍率を取得する（6時間キャッシュ）。

    返却キー:
        buy_margin   : 信用買い残（株数）
        sell_margin  : 信用売り残（株数）
        lending_ratio: 貸借倍率
        date         : データ基準日（あれば）
        source       : データソース名
    """
    # .T サフィックスを除去して4桁コードを作成
    code4 = ticker.replace(".T", "").strip().zfill(4)

    # 海外銘柄（数字4桁でない場合）は対応外
    if not code4.isdigit():
        return {}

    # J-Quants が設定されていれば優先使用
    try:
        refresh_token = st.secrets.get("JQUANTS_REFRESH_TOKEN", "")
        if refresh_token and len(refresh_token) > 10:
            data = _fetch_jquants_margin(code4, refresh_token)
            if data:
                data["source"] = "J-Quants"
                return data
    except Exception:
        pass

    # フォールバック: Kabutan スクレイピング
    try:
        data = _scrape_kabutan(code4)
        if data:
            data["source"] = "Kabutan"
            return data
    except Exception:
        pass

    return {}


def format_margin_text(margin: dict) -> str:
    """信用残データを AI プロンプト用テキストに変換する。"""
    if not margin:
        return "信用残データなし"

    lines = []
    buy = margin.get("buy_margin")
    sell = margin.get("sell_margin")
    ratio = margin.get("lending_ratio")

    if buy is not None:
        lines.append(f"信用買い残: {buy:,.0f} 株")
    if sell is not None:
        lines.append(f"信用売り残: {sell:,.0f} 株")
    if ratio is not None:
        lines.append(f"貸借倍率: {ratio:.2f} 倍")
        if ratio >= 10:
            lines.append("  → 買い残が売り残を大きく上回る（過熱感・売り圧力リスクあり）")
        elif ratio >= 3:
            lines.append("  → 買い残優勢（信用買い多め）")
        elif ratio <= 0.5:
            lines.append("  → 売り残優勢（空売り多め・踏み上げ期待）")
    if margin.get("date"):
        lines.append(f"基準日: {margin['date']}")

    return "\n".join(lines)

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import yfinance as yf
import streamlit as st
from lxml import html as lhtml


# ─── 出版社優先度 ──────────────────────────────────────────────────────────

_NIKKEI_KEYWORDS = ("日本経済新聞", "日経", "nikkei")


def _publisher_priority(publisher: str) -> int:
    """出版社の優先度を返す（0 = 最高優先）。"""
    p = publisher.lower()
    if any(k.lower() in p for k in _NIKKEI_KEYWORDS):
        return 0
    if "reuters" in p or "ロイター" in p:
        return 1
    if "bloomberg" in p or "ブルームバーグ" in p:
        return 2
    if "kabutan" in p or "株探" in p:
        return 3
    if "東洋経済" in p or "toyokeizai" in p:
        return 4
    return 9


def is_nikkei_publisher(publisher: str) -> bool:
    """日経の出版社かどうかを返す。"""
    return _publisher_priority(publisher) == 0


# ─── Google News RSS（日経専用フェッチ）─────────────────────────────────

def _fetch_google_news_rss_raw(
    query: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> list[dict]:
    """
    Google News RSS から記事を取得する（キャッシュなし、日本語モード）。
    site:nikkei.com のような絞り込みクエリに対応。
    """
    try:
        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; kabu-dashboard/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items: list[dict] = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date_str = item.findtext("pubDate", "")
            source_el = item.find("source")
            publisher = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else "日本経済新聞"
            )

            if not title or not pub_date_str:
                continue

            # Google News のタイトルに末尾 " - 出版社名" が付く場合を除去
            suffix = f" - {publisher}"
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()

            try:
                pub_dt = pd.Timestamp(pub_date_str)
                if pub_dt.tz is not None:
                    pub_dt = pub_dt.tz_convert("UTC").tz_localize(None)
            except Exception:
                continue

            if pub_dt < start_dt or pub_dt > end_dt:
                continue

            items.append({
                "pub_dt": pub_dt,
                "title": title,
                "publisher": publisher,
                "link": link,
                "uuid": f"gnews_{abs(hash(link))}",
            })

        return items

    except Exception:
        return []


# ─── yfinance ニュースフェッチ ─────────────────────────────────────────────

def _fetch_yfinance_news_raw(
    ticker: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> list[dict]:
    """yfinance からニュースを取得する（キャッシュなし）。"""
    try:
        news_raw = yf.Ticker(ticker).news
    except Exception:
        return []

    if not news_raw:
        return []

    items: list[dict] = []
    for item in news_raw:
        parsed = _parse_news_item(item)
        if parsed is None:
            continue
        if parsed["pub_dt"] < start_dt or parsed["pub_dt"] > end_dt:
            continue
        items.append(parsed)

    return items


# ─── 決算イベント ──────────────────────────────────────────────────────────

def _fetch_kabutan_earnings(ticker: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> list[dict]:
    """Kabutan の決算発表日ページから決算イベントを取得する（yfinance フォールバック用）。"""
    try:
        import requests as _req
        from lxml import html as _lhtml

        code4 = ticker.replace(".T", "").strip().zfill(4)
        url = f"https://kabutan.jp/stock/finance?code={code4}"
        r = _req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []

        tree = _lhtml.fromstring(r.content)

        # 決算発表日テーブル（通常 table[1] に予定/実績がある）
        # 「決算」タブのテーブルから発表日を探す
        events = []

        # 方法1: ページ内のテキストから「決算発表日」情報を抽出
        # kabutan の /stock/finance ページの構造に依存
        tables = tree.xpath('//table')
        for table in tables:
            rows = table.xpath('.//tr')
            for row in rows:
                cells = row.xpath('.//td|.//th')
                texts = [c.text_content().strip() for c in cells]
                # 日付パターンを探す（例: "2025/02/06", "25/02/06"）
                for text in texts:
                    import re
                    # YYYY/MM/DD or YY/MM/DD パターン
                    m = re.search(r'(\d{2,4})[/\-](\d{1,2})[/\-](\d{1,2})', text)
                    if m:
                        try:
                            y, mo, d = m.group(1), m.group(2), m.group(3)
                            if len(y) == 2:
                                y = "20" + y
                            dt = pd.Timestamp(f"{y}-{mo}-{d}")
                            if start_dt <= dt <= end_dt:
                                # 同じ日付が既に追加されていないか確認
                                date_str = dt.strftime("%Y-%m-%d")
                                if not any(e["date"] == date_str for e in events):
                                    # 決算に関連するテキストを探す
                                    row_text = " ".join(texts)
                                    if any(kw in row_text for kw in ["決算", "本決算", "中間", "1Q", "2Q", "3Q", "四半期", "通期"]):
                                        events.append({
                                            "date": date_str,
                                            "period_end": _nearest_quarter_end(dt).strftime("%Y-%m-%d"),
                                            "revenue": None,
                                            "operating_income": None,
                                            "eps_actual": None,
                                            "eps_estimate": None,
                                            "beat": None,
                                        })
                        except Exception:
                            continue
        return events
    except Exception:
        return []


def _fetch_jquants_earnings(ticker: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> list[dict]:
    """J-Quants API から決算発表日を取得する（yfinance フォールバック用）。"""
    try:
        refresh_token = st.secrets.get("JQUANTS_REFRESH_TOKEN", "")
        if not refresh_token or len(refresh_token) < 10:
            return []

        import requests as _req
        code = ticker.replace(".T", "").strip().zfill(4)

        from modules.fundamental import _get_jquants_access_token
        access_token = _get_jquants_access_token(refresh_token)

        resp = _req.get(
            "https://api.jquants.com/v1/fins/statements",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"code": code},
            timeout=15,
        )
        resp.raise_for_status()
        statements = resp.json().get("statements", [])

        events = []
        for stmt in statements:
            disc_date = stmt.get("DisclosedDate", "")
            period_end = stmt.get("CurrentPeriodEndDate", "")
            if not disc_date:
                continue
            try:
                dt = pd.Timestamp(disc_date)
                if start_dt <= dt <= end_dt:
                    net_sales = stmt.get("NetSales")
                    op_profit = stmt.get("OperatingProfit")
                    events.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "period_end": period_end,
                        "revenue": float(net_sales) if net_sales else None,
                        "operating_income": float(op_profit) if op_profit else None,
                        "eps_actual": None,
                        "eps_estimate": None,
                        "beat": None,
                    })
            except Exception:
                continue
        return events
    except Exception:
        return []


@st.cache_data(ttl=3600)
def fetch_earnings_events(ticker: str, chart_start: str, chart_end: str) -> list[dict]:
    """
    チャート表示期間内の決算日データを取得する。
    yfinance → J-Quants → Kabutan の順にフォールバック。

    Returns:
        list of dict:
        [{
            "date": "2024-11-08",          # str (YYYY-MM-DD)
            "period_end": "2024-09-30",    # 決算期末日
            "revenue": 4_500_000_000_000,  # 売上高（円）or None
            "operating_income": 320_000_000_000,  # 営業利益（円）or None
            "eps_actual": 1250.5,          # EPS 実績 or None
            "eps_estimate": 1180.0,        # EPS 予想 or None
            "beat": True,                  # 予想超過フラグ or None
        }]
    """
    start_dt = pd.Timestamp(chart_start)
    end_dt = pd.Timestamp(chart_end)

    # ── ソース1: yfinance ──────────────────────────────────────
    events = []
    try:
        t = yf.Ticker(ticker)
        earn_df = t.get_earnings_dates(limit=40)

        if earn_df is not None and not earn_df.empty:
            if earn_df.index.tz is not None:
                earn_df.index = earn_df.index.tz_localize(None)

            earn_df = earn_df[(earn_df.index >= start_dt) & (earn_df.index <= end_dt)]

            try:
                qf = t.quarterly_income_stmt
            except Exception:
                qf = None

            for dt, row in earn_df.iterrows():
                date_str = dt.strftime("%Y-%m-%d")
                eps_est = row.get("EPS Estimate") or row.get("eps_estimate")
                eps_act = row.get("Reported EPS") or row.get("reported_eps")
                rev, op_inc = _lookup_quarterly_financials(qf, dt)

                beat = None
                if pd.notna(eps_act) and pd.notna(eps_est) and eps_est != 0:
                    beat = float(eps_act) > float(eps_est)

                events.append({
                    "date": date_str,
                    "period_end": _nearest_quarter_end(dt).strftime("%Y-%m-%d"),
                    "revenue": rev,
                    "operating_income": op_inc,
                    "eps_actual": float(eps_act) if pd.notna(eps_act) else None,
                    "eps_estimate": float(eps_est) if pd.notna(eps_est) else None,
                    "beat": beat,
                })
    except Exception:
        pass

    if events:
        return events

    # ── ソース2: J-Quants（yfinance が空の場合）──────────────────
    events = _fetch_jquants_earnings(ticker, start_dt, end_dt)
    if events:
        return events

    # ── ソース3: Kabutan（最終フォールバック）─────────────────────
    return _fetch_kabutan_earnings(ticker, start_dt, end_dt)


# ─── Kabutan ニューススクレイピング ──────────────────────────────────────

def _fetch_kabutan_news_raw(
    ticker: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> list[dict]:
    """Kabutan の銘柄ニュースページからニュースを取得する。"""
    code4 = ticker.replace(".T", "").strip().zfill(4)
    url = f"https://kabutan.jp/stock/news?code={code4}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; kabu-dashboard/1.0)"},
            timeout=10,
        )
        resp.raise_for_status()
        tree = lhtml.fromstring(resp.content)
    except Exception:
        return []

    items: list[dict] = []
    rows = tree.xpath('//table[contains(@class,"s_news_list")]//tr')
    for row in rows:
        try:
            tds = row.xpath(".//td")
            if len(tds) < 3:
                continue

            # 1列目: 日時 "26/03/27 15:38"
            date_text = tds[0].text_content().strip()
            # \xa0（非分割スペース）で日付と時間を分割
            date_part = date_text.split("\xa0")[0].split(" ")[0].strip()
            # "26/03/27" → "2026/03/27"
            parts = date_part.split("/")
            if len(parts) == 3 and len(parts[0]) == 2:
                date_part = f"20{parts[0]}/{parts[1]}/{parts[2]}"
            try:
                # JST日付をUTC正規化（Google Newsと統一）
                pub_dt = pd.Timestamp(date_part, tz="Asia/Tokyo")
                pub_dt = pub_dt.tz_convert("UTC").tz_localize(None)
            except Exception:
                continue

            if pub_dt < start_dt or pub_dt > end_dt:
                continue

            # 3列目: ニュースタイトル（リンク付き）
            link_el = tds[2].xpath(".//a")
            if not link_el:
                title = tds[2].text_content().strip()
                link = ""
            else:
                title = link_el[0].text_content().strip()
                href = link_el[0].get("href", "")
                link = f"https://kabutan.jp{href}" if href.startswith("/") else href

            if not title:
                continue

            items.append({
                "pub_dt": pub_dt,
                "title": title,
                "publisher": "株探",
                "link": link,
                "uuid": f"kabutan_{abs(hash(link or title))}",
            })
        except Exception:
            continue

    return items


# ─── Google News RSS（汎用クエリ）───────────────────────────────────────

def _fetch_google_news_general_raw(
    query: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> list[dict]:
    """
    Google News RSS でサイト制限なし全ソースからニュースを取得。
    Bloomberg、ロイター、東洋経済などを補完。
    """
    try:
        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; kabu-dashboard/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items: list[dict] = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date_str = item.findtext("pubDate", "")
            source_el = item.find("source")
            publisher = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else "不明"
            )

            if not title or not pub_date_str:
                continue

            suffix = f" - {publisher}"
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()

            try:
                pub_dt = pd.Timestamp(pub_date_str)
                if pub_dt.tz is not None:
                    pub_dt = pub_dt.tz_convert("UTC").tz_localize(None)
            except Exception:
                continue

            if pub_dt < start_dt or pub_dt > end_dt:
                continue

            items.append({
                "pub_dt": pub_dt,
                "title": title,
                "publisher": publisher,
                "link": link,
                "uuid": f"gnews_gen_{abs(hash(link))}",
            })

        return items

    except Exception:
        return []


# ─── 最新ニュース取得（チャート期間に依存しない）─────────────────────────

@st.cache_data(ttl=1800)
def fetch_latest_news(
    ticker: str,
    company_name: str = "",
    max_items: int = 30,
) -> list[dict]:
    """
    直近30日間の最新ニュースを全ソースから収集する。
    ポートフォリオ分析など、チャート期間に依存しない用途向け。
    """
    end_dt = pd.Timestamp.now()
    start_dt = end_dt - pd.Timedelta(days=30)
    code4 = ticker.replace(".T", "").strip()

    # 全ソースから並列的に収集
    nikkei_query = f"{company_name} {code4} site:nikkei.com" if company_name else f"{code4} site:nikkei.com"
    nikkei_items = _fetch_google_news_rss_raw(nikkei_query, start_dt, end_dt)

    general_query = f"{company_name} {code4} 株" if company_name else f"{code4} 株"
    general_items = _fetch_google_news_general_raw(general_query, start_dt, end_dt)

    yf_items = _fetch_yfinance_news_raw(ticker, start_dt, end_dt)
    kabutan_items = _fetch_kabutan_news_raw(ticker, start_dt, end_dt)

    # TDNet 適時開示
    tdnet_items = []
    try:
        from modules.tdnet import fetch_tdnet_disclosures
        disclosures = fetch_tdnet_disclosures(ticker)
        for d in disclosures:
            try:
                pub_dt = pd.Timestamp(d["date"])
                if pub_dt >= start_dt and pub_dt <= end_dt:
                    impact = d.get("impact", "neutral")
                    prefix = {"positive": "📈", "negative": "📉"}.get(impact, "📋")
                    tdnet_items.append({
                        "pub_dt": pub_dt,
                        "title": f"[{d.get('category', 'IR')}] {d['title']}",
                        "publisher": "TDNet適時開示",
                        "link": d.get("link", ""),
                        "uuid": f"tdnet_{abs(hash(d.get('link', d['title'])))}",
                    })
            except Exception:
                continue
    except Exception:
        pass

    # マージ＋重複除去（タイトル先頭30文字）
    seen: set[str] = set()
    merged: list[dict] = []
    # TDNet→日経→株探→汎用ニュース→yfinance の優先順
    for item in tdnet_items + nikkei_items + kabutan_items + general_items + yf_items:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            merged.append(item)

    # 日付降順ソート（最新が先頭）
    merged.sort(key=lambda x: x["pub_dt"], reverse=True)
    return merged[:max_items]


# ─── ニュースイベント ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_news_events(
    ticker: str,
    chart_start: str,
    chart_end: str,
    company_name: str = "",
) -> list[dict]:
    """
    チャート表示期間内のニュースを取得する。
    日経電子版（Google News RSS 経由）を優先し、yfinance の記事で補完する。

    Returns:
        list of dict:
        [{
            "date": "2024-11-10",
            "title": "主要ニュース見出し",
            "publisher": "日本経済新聞",
            "link": "https://...",
            "uuid": "...",
            "all_items": [{"title": ..., "publisher": ..., "link": ..., "uuid": ...}]
        }]
    """
    start_dt = pd.Timestamp(chart_start)
    end_dt = pd.Timestamp(chart_end)
    code_4 = ticker.replace(".T", "").strip()

    # 1. 日経記事を Google News RSS で取得
    nikkei_query = f"{code_4} site:nikkei.com"
    if company_name:
        nikkei_query = f"{company_name} {code_4} site:nikkei.com"
    nikkei_items = _fetch_google_news_rss_raw(nikkei_query, start_dt, end_dt)

    # 2. 株探ニュースで補完
    kabutan_items = _fetch_kabutan_news_raw(ticker, start_dt, end_dt)

    # 3. Google News 汎用（Bloomberg, ロイター, 東洋経済等）
    general_query = f"{company_name} {code_4} 株" if company_name else f"{code_4} 株"
    general_items = _fetch_google_news_general_raw(general_query, start_dt, end_dt)

    # 4. yfinance ニュースで補完
    yf_items = _fetch_yfinance_news_raw(ticker, start_dt, end_dt)

    # 5. マージ（日経→株探→汎用→yfinance）+ タイトル先頭30文字で重複除去
    seen: set[str] = set()
    merged: list[dict] = []
    for item in nikkei_items + kabutan_items + general_items + yf_items:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            merged.append(item)

    # 4. 日付ごとにグループ化
    events: list[dict] = []
    for item in merged:
        date_str = item["pub_dt"].strftime("%Y-%m-%d")
        news_item = {
            "title": item["title"],
            "publisher": item["publisher"],
            "link": item["link"],
            "uuid": item["uuid"],
        }
        existing = next((e for e in events if e["date"] == date_str), None)
        if existing:
            existing["all_items"].append(news_item)
        else:
            events.append({
                "date": date_str,
                "title": news_item["title"],
                "publisher": news_item["publisher"],
                "link": news_item["link"],
                "uuid": news_item["uuid"],
                "all_items": [news_item],
            })

    # 5. 各日の all_items を出版社優先度順にソート（安定ソート）
    #    日経が最初になるように並び替え、代表記事も更新する
    for ev in events:
        ev["all_items"].sort(key=lambda x: _publisher_priority(x["publisher"]))
        top = ev["all_items"][0]
        ev["title"] = top["title"]
        ev["publisher"] = top["publisher"]
        ev["link"] = top["link"]
        ev["uuid"] = top["uuid"]

    return events


# ─── ユーティリティ ────────────────────────────────────────────────────────

def _parse_news_item(item: dict) -> dict | None:
    """
    yfinance のニュースアイテムをパースする。
    新形式（content ネスト）と旧形式（フラット）の両方に対応。
    """
    try:
        # ── 新形式: item["content"] にネストされている ──────────────
        if "content" in item and isinstance(item["content"], dict):
            content = item["content"]

            title = content.get("title", "")
            pub_date_str = content.get("pubDate") or content.get("displayTime", "")
            publisher = (content.get("provider") or {}).get("displayName", "")

            # リンク: previewUrl（ヤフーファイナンス）を優先。canonicalUrl は有料記事が多い
            link = content.get("previewUrl", "")
            if not link:
                canonical = content.get("canonicalUrl") or {}
                link = canonical.get("url", "")
            if not link:
                click = content.get("clickThroughUrl") or {}
                link = click.get("url", "")

            uuid = content.get("id") or item.get("id", "")

            # pubDate は ISO 8601 形式 "2026-03-02T10:30:00Z"
            if not pub_date_str:
                return None
            pub_dt = pd.Timestamp(pub_date_str).tz_localize(None) if pd.Timestamp(pub_date_str).tz is None \
                else pd.Timestamp(pub_date_str).tz_convert("UTC").tz_localize(None)

        # ── 旧形式: フラット構造 ─────────────────────────────────────
        else:
            pub_ts = item.get("providerPublishTime", 0)
            if not pub_ts:
                return None
            pub_dt = pd.Timestamp(pub_ts, unit="s")
            title = item.get("title", "")
            publisher = item.get("publisher", "")
            link = item.get("link", "")
            uuid = item.get("uuid", "")

        if not title:
            return None

        return {
            "pub_dt": pub_dt,
            "title": title,
            "publisher": publisher,
            "link": link,
            "uuid": uuid,
        }

    except Exception:
        return None


def _lookup_quarterly_financials(
    qf: pd.DataFrame | None,
    earnings_dt: pd.Timestamp,
) -> tuple[float | None, float | None]:
    """決算発表日直前の四半期カラムから売上高・営業利益を取得する。"""
    if qf is None or qf.empty:
        return None, None

    candidates = []
    for c in qf.columns:
        if isinstance(c, pd.Timestamp):
            c_naive = c.tz_localize(None) if c.tz is not None else c
            diff = (earnings_dt - c_naive).days
            if 0 <= diff <= 120:
                candidates.append(c)

    if not candidates:
        return None, None

    col = max(candidates)

    rev = None
    for key in ["Total Revenue", "Revenue", "TotalRevenue"]:
        if key in qf.index:
            val = qf.loc[key, col]
            if pd.notna(val):
                rev = float(val)
            break

    op_inc = None
    for key in ["Operating Income", "OperatingIncome", "EBIT"]:
        if key in qf.index:
            val = qf.loc[key, col]
            if pd.notna(val):
                op_inc = float(val)
            break

    return rev, op_inc


def _nearest_quarter_end(dt: pd.Timestamp) -> pd.Timestamp:
    """dt より前で直近の四半期末（3/6/9/12月末）を返す。"""
    m = dt.month
    if m <= 3:
        return pd.Timestamp(dt.year - 1, 12, 31)
    elif m <= 6:
        return pd.Timestamp(dt.year, 3, 31)
    elif m <= 9:
        return pd.Timestamp(dt.year, 6, 30)
    else:
        return pd.Timestamp(dt.year, 9, 30)


def get_tdnet_url(ticker: str) -> str:
    """TDNET 適時開示情報の一覧 URL を返す（4 桁証券コードを使用）。"""
    code = ticker.replace(".T", "").strip()
    return f"https://www.release.tdnet.info/inbs/I_list_001_{code}.html"


def get_edinet_url(ticker: str) -> str:
    """EDINET での企業検索 URL を返す。"""
    code = ticker.replace(".T", "").strip()
    return f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S1={code}"

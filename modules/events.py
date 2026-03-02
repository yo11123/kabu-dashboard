import pandas as pd
import yfinance as yf
import streamlit as st


@st.cache_data(ttl=3600)
def fetch_earnings_events(ticker: str, chart_start: str, chart_end: str) -> list[dict]:
    """
    チャート表示期間内の決算日データを取得する。

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
    try:
        t = yf.Ticker(ticker)
        earn_df = t.get_earnings_dates(limit=40)
    except Exception:
        return []

    if earn_df is None or earn_df.empty:
        return []

    start_dt = pd.Timestamp(chart_start)
    end_dt = pd.Timestamp(chart_end)

    # タイムゾーンを除去して比較
    if earn_df.index.tz is not None:
        earn_df.index = earn_df.index.tz_localize(None)

    earn_df = earn_df[(earn_df.index >= start_dt) & (earn_df.index <= end_dt)]

    if earn_df.empty:
        return []

    try:
        qf = t.quarterly_income_stmt
    except Exception:
        qf = None

    events = []
    for dt, row in earn_df.iterrows():
        date_str = dt.strftime("%Y-%m-%d")

        # カラム名は yfinance バージョンによって異なる場合があるため柔軟に対応
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

    return events


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


@st.cache_data(ttl=3600)
def fetch_news_events(ticker: str, chart_start: str, chart_end: str) -> list[dict]:
    """
    チャート表示期間内のニュースを取得する。
    同一日に複数のニュースがある場合は all_items にまとめる。

    yfinance の新形式（content ネスト）と旧形式（フラット）の両方に対応する。

    Returns:
        list of dict:
        [{
            "date": "2024-11-10",
            "title": "主要ニュース見出し",
            "publisher": "Reuters",
            "link": "https://...",
            "uuid": "abc123",
            "all_items": [{"title": ..., "publisher": ..., "link": ..., "uuid": ...}]
        }]
    """
    try:
        t = yf.Ticker(ticker)
        news_raw = t.news
    except Exception:
        return []

    if not news_raw:
        return []

    start_dt = pd.Timestamp(chart_start)
    end_dt = pd.Timestamp(chart_end)

    events: list[dict] = []

    for item in news_raw:
        parsed = _parse_news_item(item)
        if parsed is None:
            continue

        pub_dt = parsed["pub_dt"]
        if pub_dt < start_dt or pub_dt > end_dt:
            continue

        date_str = pub_dt.strftime("%Y-%m-%d")
        news_item = {
            "title": parsed["title"],
            "publisher": parsed["publisher"],
            "link": parsed["link"],
            "uuid": parsed["uuid"],
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

    return events


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


def get_tdnet_url(ticker: str) -> str:
    """TDNET 適時開示情報の一覧 URL を返す（4 桁証券コードを使用）。"""
    code = ticker.replace(".T", "").strip()
    return f"https://www.release.tdnet.info/inbs/I_list_001_{code}.html"


def get_edinet_url(ticker: str) -> str:
    """EDINET での企業検索 URL を返す。"""
    code = ticker.replace(".T", "").strip()
    return f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S1={code}"

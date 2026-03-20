"""
市場全体の指標・マクロデータの取得・整形モジュール

yfinance で取得可能な主要指標をカバーし、
AI 分析用テキストおよびダッシュボード表示用データを提供する。
"""

import pandas as pd
import streamlit as st
import yfinance as yf

# ─── 指標定義 ─────────────────────────────────────────────────────────
# (name, ticker, category, unit, description)

INDICATORS: list[tuple[str, str, str, str, str]] = [
    # ── センチメント ──
    ("VIX（恐怖指数）",     "^VIX",      "sentiment", "",    "S&P500の予想変動率。20超で警戒、30超で極度の恐怖"),
    ("SKEW指数",            "^SKEW",     "sentiment", "",    "テールリスク警戒度。150超で暴落警戒"),

    # ── セクター ──
    ("SOX（半導体指数）",   "^SOX",      "sector",    "USD", "フィラデルフィア半導体指数。AI・テック相場の先行指標"),
    ("ダウ輸送株平均",      "^DJT",      "sector",    "USD", "実体経済の裏付けを確認するダウ理論の要"),
    ("ラッセル2000",        "^RUT",      "sector",    "USD", "米小型株。リスクオン/オフの温度計"),

    # ── 主要株価指数 ──
    ("日経平均",            "^N225",     "index",     "円",  "日経225"),
    ("TOPIX（ETF）",        "1306.T",    "index",     "円",  "東証株価指数（TOPIX連動ETF）"),
    ("S&P 500",             "^GSPC",     "index",     "USD", "米大型株500銘柄"),
    ("ナスダック総合",      "^IXIC",     "index",     "USD", "テクノロジー中心"),
    ("ダウ平均",            "^DJI",      "index",     "USD", "米主要30銘柄"),

    # ── 債券・金利 ──
    ("米10年債利回り",      "^TNX",      "bond",      "%",   "長期金利の代表。株式バリュエーションに直接影響"),
    ("米5年債利回り",       "^FVX",      "bond",      "%",   "中期金利"),
    ("米30年債利回り",      "^TYX",      "bond",      "%",   "超長期金利"),
    ("米13週T-Bill",        "^IRX",      "bond",      "%",   "短期金利。FRB政策を最も敏感に反映"),

    # ── コモディティ ──
    ("金（Gold）",          "GC=F",      "commodity",  "USD", "有事の金。インフレ・地政学リスクで上昇"),
    ("WTI原油",             "CL=F",      "commodity",  "USD", "エネルギー・インフレ指標"),
    ("銅（Copper）",        "HG=F",      "commodity",  "USD", "ドクター・カッパー。景気の体温計"),

    # ── 為替 ──
    ("ドルインデックス",    "DX-Y.NYB",  "fx",        "",    "主要6通貨に対するドルの強さ"),
    ("ドル円（USD/JPY）",   "JPY=X",     "fx",        "円",  "日本株と高相関。円安で輸出企業に追い風"),
    ("ユーロドル",          "EURUSD=X",  "fx",        "USD", "世界最大の通貨ペア"),
]


# ─── データ取得 ────────────────────────────────────────────────────────

@st.cache_data(ttl=300)  # 5分キャッシュ
def fetch_indicator_history(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    """1指標の価格履歴を取得する。"""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        df.columns = [str(c).capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.dropna(subset=["Close"], inplace=True)
        return df if not df.empty else None
    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_market_snapshot() -> dict[str, dict]:
    """
    全市場指標の最新値・変化率をバッチ取得する。
    Returns: {name: {"value", "change", "change_pct", "ticker", "category", "unit", "description"}}
    """
    tickers = [ind[1] for ind in INDICATORS]

    try:
        raw = yf.download(
            tickers=tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return {}

    single = len(tickers) == 1
    result: dict[str, dict] = {}

    for name, ticker, category, unit, desc in INDICATORS:
        try:
            df = raw.copy() if single else raw[ticker].copy()
            if df is None or df.empty:
                continue
            df.columns = [str(c).capitalize() for c in df.columns]
            df.dropna(subset=["Close"], inplace=True)
            if len(df) < 2:
                continue

            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            change = last - prev
            change_pct = change / prev * 100 if prev != 0 else 0.0

            result[name] = {
                "value":      last,
                "change":     round(change, 4),
                "change_pct": round(change_pct, 2),
                "ticker":     ticker,
                "category":   category,
                "unit":       unit,
                "description": desc,
            }
        except Exception:
            continue

    return result


# ─── 派生指標の計算 ────────────────────────────────────────────────────

def calc_derived_indicators(snapshot: dict) -> dict[str, dict]:
    """スナップショットから派生指標を計算する。"""
    derived: dict[str, dict] = {}

    # ─ 長短金利差（イールドカーブ）: 10Y - 13W ─
    tnx = snapshot.get("米10年債利回り", {}).get("value")
    irx = snapshot.get("米13週T-Bill", {}).get("value")
    if tnx is not None and irx is not None:
        spread = round(tnx - irx, 3)
        derived["長短金利差（10Y-13W）"] = {
            "value":  spread,
            "unit":   "%",
            "label":  "逆イールド" if spread < 0 else "順イールド",
            "signal": "bearish" if spread < 0 else ("neutral" if spread < 0.5 else "bullish"),
        }

    # ─ NT倍率: 日経225 / TOPIX ─
    n225  = snapshot.get("日経平均", {}).get("value")
    topix = snapshot.get("TOPIX（ETF）", {}).get("value")
    if n225 is not None and topix is not None and topix > 0:
        nt = round(n225 / topix, 2)
        derived["NT倍率"] = {
            "value": nt,
            "unit":  "倍",
            "label": "日経225÷TOPIX",
        }

    # ─ VIX 解釈 ─
    vix = snapshot.get("VIX（恐怖指数）", {}).get("value")
    if vix is not None:
        if vix > 30:
            label, signal = "極度の恐怖", "extreme_fear"
        elif vix > 20:
            label, signal = "警戒", "fear"
        elif vix > 15:
            label, signal = "通常", "neutral"
        else:
            label, signal = "楽観", "greed"
        derived["VIX解釈"] = {"value": vix, "label": label, "signal": signal}

    # ─ 実現ボラティリティ（日経225, 20日HV）─
    n225_data = snapshot.get("日経平均")
    if n225_data:
        df = fetch_indicator_history("^N225", "3mo")
        if df is not None and len(df) >= 20:
            returns = df["Close"].pct_change().dropna()
            hv20 = float(returns.tail(20).std() * (252 ** 0.5) * 100)
            derived["日経HV20"] = {
                "value": round(hv20, 1),
                "unit":  "%",
                "label": f"日経225の20日実現ボラティリティ: {hv20:.1f}%",
            }

    return derived


# ─── AI 分析用テキスト生成 ─────────────────────────────────────────────

@st.cache_data(ttl=3600)  # 1時間キャッシュ（AI分析のキャッシュキーを安定させるため）
def fetch_market_context_text() -> str:
    """AI分析プロンプトに追加するマーケットコンテキストテキストを生成する。"""
    snapshot = fetch_market_snapshot()
    if not snapshot:
        return ""

    derived = calc_derived_indicators(snapshot)
    lines = ["## マーケット環境（直近）"]

    # VIX
    vix = snapshot.get("VIX（恐怖指数）")
    vix_label = derived.get("VIX解釈", {}).get("label", "")
    if vix:
        lines.append(f"- VIX: {vix['value']:.1f}（{vix_label}、前日比{vix['change_pct']:+.1f}%）")

    # SKEW
    skew = snapshot.get("SKEW指数")
    if skew:
        skew_note = "暴落警戒" if skew["value"] > 150 else "通常範囲"
        lines.append(f"- SKEW: {skew['value']:.0f}（{skew_note}）")

    # 長短金利差
    yc = derived.get("長短金利差（10Y-13W）")
    if yc:
        lines.append(f"- 長短金利差: {yc['value']:+.3f}%（{yc['label']}）")

    # 米10年債
    tnx = snapshot.get("米10年債利回り")
    if tnx:
        lines.append(f"- 米10年債利回り: {tnx['value']:.2f}%（{tnx['change_pct']:+.1f}%）")

    # ドル円
    usdjpy = snapshot.get("ドル円（USD/JPY）")
    if usdjpy:
        lines.append(f"- ドル円: {usdjpy['value']:.1f}円（{usdjpy['change_pct']:+.1f}%）")

    # 金
    gold = snapshot.get("金（Gold）")
    if gold:
        lines.append(f"- 金: ${gold['value']:,.1f}（{gold['change_pct']:+.1f}%）")

    # 原油
    oil = snapshot.get("WTI原油")
    if oil:
        lines.append(f"- 原油: ${oil['value']:.1f}（{oil['change_pct']:+.1f}%）")

    # 銅
    copper = snapshot.get("銅（Copper）")
    if copper:
        lines.append(f"- 銅: ${copper['value']:.2f}（{copper['change_pct']:+.1f}%）")

    # SOX
    sox = snapshot.get("SOX（半導体指数）")
    if sox:
        lines.append(f"- SOX半導体指数: {sox['value']:,.0f}（{sox['change_pct']:+.1f}%）")

    # ラッセル2000
    rut = snapshot.get("ラッセル2000")
    if rut:
        lines.append(f"- ラッセル2000: {rut['value']:,.0f}（{rut['change_pct']:+.1f}%）")

    # NT倍率
    nt = derived.get("NT倍率")
    if nt:
        lines.append(f"- NT倍率: {nt['value']:.2f}倍")

    # DXY
    dxy = snapshot.get("ドルインデックス")
    if dxy:
        lines.append(f"- ドルインデックス: {dxy['value']:.1f}（{dxy['change_pct']:+.1f}%）")

    # 実現ボラティリティ
    hv = derived.get("日経HV20")
    if hv:
        lines.append(f"- 日経HV20: {hv['value']:.1f}%")

    return "\n".join(lines) if len(lines) > 1 else ""

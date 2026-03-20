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
    """AI分析プロンプトに追加するマーケットコンテキストテキストを生成する。

    全指標の最新値・前日比を網羅的に含め、AIが市場全体の環境を
    踏まえたうえで個別銘柄を分析できるようにする。
    """
    snapshot = fetch_market_snapshot()
    if not snapshot:
        return ""

    derived = calc_derived_indicators(snapshot)
    lines = ["## マーケット環境（直近の全指標データ）"]

    # ─── センチメント ─────────────────────────────────────────
    lines.append("\n### センチメント")
    vix = snapshot.get("VIX（恐怖指数）")
    vix_label = derived.get("VIX解釈", {}).get("label", "")
    if vix:
        lines.append(f"- VIX（恐怖指数）: {vix['value']:.1f}（{vix_label}、前日比{vix['change_pct']:+.1f}%）"
                     f"  ※20超で警戒、30超で極度の恐怖")
    skew = snapshot.get("SKEW指数")
    if skew:
        skew_note = "テールリスク警戒" if skew["value"] > 150 else "通常範囲"
        lines.append(f"- SKEW指数: {skew['value']:.0f}（{skew_note}）  ※150超で暴落警戒")
    hv = derived.get("日経HV20")
    if hv:
        lines.append(f"- 日経225 実現ボラティリティ（HV20）: {hv['value']:.1f}%")

    # ─── 主要株価指数 ─────────────────────────────────────────
    lines.append("\n### 主要株価指数")
    for name in ["日経平均", "TOPIX（ETF）", "S&P 500", "ナスダック総合", "ダウ平均"]:
        d = snapshot.get(name)
        if d:
            unit = d.get("unit", "")
            val = f"{d['value']:,.0f}" if d["value"] >= 100 else f"{d['value']:,.2f}"
            lines.append(f"- {name}: {val} {unit}（前日比{d['change_pct']:+.1f}%）")

    # ─── セクター指標 ─────────────────────────────────────────
    lines.append("\n### セクター指標")
    for name in ["SOX（半導体指数）", "ダウ輸送株平均", "ラッセル2000"]:
        d = snapshot.get(name)
        if d:
            lines.append(f"- {name}: {d['value']:,.0f}（前日比{d['change_pct']:+.1f}%）"
                         f"  ※{d['description']}")

    # ─── 債券・金利 ───────────────────────────────────────────
    lines.append("\n### 債券・金利")
    for name in ["米10年債利回り", "米5年債利回り", "米30年債利回り", "米13週T-Bill"]:
        d = snapshot.get(name)
        if d:
            lines.append(f"- {name}: {d['value']:.2f}%（前日比{d['change_pct']:+.1f}%）")
    yc = derived.get("長短金利差（10Y-13W）")
    if yc:
        lines.append(f"- 長短金利差（10Y-13W）: {yc['value']:+.3f}%（{yc['label']}）"
                     f"  ※マイナスで逆イールド→景気後退リスク上昇")

    # ─── コモディティ ─────────────────────────────────────────
    lines.append("\n### コモディティ")
    gold = snapshot.get("金（Gold）")
    if gold:
        lines.append(f"- 金（Gold）: ${gold['value']:,.1f}（前日比{gold['change_pct']:+.1f}%）"
                     f"  ※安全資産、インフレ・地政学リスクで上昇")
    oil = snapshot.get("WTI原油")
    if oil:
        lines.append(f"- WTI原油: ${oil['value']:.1f}（前日比{oil['change_pct']:+.1f}%）"
                     f"  ※エネルギーコスト・インフレに影響")
    copper = snapshot.get("銅（Copper）")
    if copper:
        lines.append(f"- 銅（ドクター・カッパー）: ${copper['value']:.2f}（前日比{copper['change_pct']:+.1f}%）"
                     f"  ※景気の体温計、上昇は需要拡大を示唆")

    # ─── 為替 ─────────────────────────────────────────────────
    lines.append("\n### 為替")
    dxy = snapshot.get("ドルインデックス")
    if dxy:
        lines.append(f"- ドルインデックス（DXY）: {dxy['value']:.1f}（前日比{dxy['change_pct']:+.1f}%）"
                     f"  ※ドル高は新興国・コモディティに逆風")
    usdjpy = snapshot.get("ドル円（USD/JPY）")
    if usdjpy:
        lines.append(f"- ドル円: {usdjpy['value']:.1f}円（前日比{usdjpy['change_pct']:+.1f}%）"
                     f"  ※円安で日本輸出企業に追い風、円高は逆風")
    eurusd = snapshot.get("ユーロドル")
    if eurusd:
        lines.append(f"- ユーロドル: {eurusd['value']:.4f}（前日比{eurusd['change_pct']:+.1f}%）")

    # ─── バリュエーション・派生指標 ──────────────────────────
    lines.append("\n### バリュエーション・派生指標")
    nt = derived.get("NT倍率")
    if nt:
        lines.append(f"- NT倍率: {nt['value']:.2f}倍  ※拡大は値がさ株集中、市場の裾野が狭い状態")

    # ─── 分析ガイド ──────────────────────────────────────────
    lines.append(
        "\n上記のマーケット環境データをもとに、対象銘柄への影響を分析に必ず反映してください。"
        "例: VIX高水準→リスクオフ環境、逆イールド→景気後退リスク、"
        "円安→輸出企業に有利、金利上昇→グロース株に逆風、SOX好調→半導体関連に追い風、など。"
    )

    return "\n".join(lines)

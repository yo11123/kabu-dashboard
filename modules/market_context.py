"""
市場全体の指標・マクロデータの取得・整形モジュール

yfinance で取得可能な主要指標 + FRED API のマクロ経済指標をカバーし、
AI 分析用テキストおよびダッシュボード表示用データを提供する。
"""

import json as _json
import logging

import pandas as pd
import requests as _requests
import streamlit as st
import yfinance as yf

_log = logging.getLogger(__name__)

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
        # MultiIndex columns 対応（yfinance 新バージョン）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]).capitalize() for c in df.columns]
        else:
            df.columns = [str(c).capitalize() for c in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        if "Close" not in df.columns:
            return None
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
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [str(c[0]).capitalize() for c in df.columns]
            else:
                df.columns = [str(c).capitalize() for c in df.columns]
            if "Close" not in df.columns:
                continue
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


# ─── サンデーダウ・サンデー日経（ウィークエンドCFD）──────────────────────


@st.cache_data(ttl=300, show_spinner=False)
def fetch_weekend_cfd() -> dict[str, dict]:
    """
    IG証券のウィークエンド取引（サンデーダウ・サンデー日経）のデータを取得する。
    週末のみ有効。平日は空辞書を返す。

    Returns: {"サンデーダウ": {"value", "change", "change_pct"}, "サンデー日経": {...}}
    """
    result: dict[str, dict] = {}

    # Investing.com のウィークエンドCFDページからスクレイピング
    _WEEKEND_SOURCES = [
        {
            "name": "サンデーダウ",
            "url": "https://api.investing.com/api/financialdata/8873/historical/chart/?interval=PT1M&pointscount=60",
            "ref_name": "ダウ平均",
            "description": "IG証券ウィークエンド取引。週末の市場センチメント先行指標",
        },
        {
            "name": "サンデー日経",
            "url": "https://api.investing.com/api/financialdata/8874/historical/chart/?interval=PT1M&pointscount=60",
            "ref_name": "日経平均",
            "description": "IG証券ウィークエンド取引。月曜の日経寄付きの先行指標",
        },
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "domain-id": "www",
    }

    for src in _WEEKEND_SOURCES:
        try:
            resp = _requests.get(src["url"], headers=headers, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            # Investing.com API のレスポンスからデータを抽出
            points = data.get("data", [])
            if not points or len(points) < 2:
                continue

            latest = points[-1]
            first = points[0]
            # データ形式: [timestamp, value] or {"date": ..., "value": ...}
            if isinstance(latest, list):
                current_val = float(latest[1])
                open_val = float(first[1])
            elif isinstance(latest, dict):
                current_val = float(latest.get("y") or latest.get("value") or latest.get("last", 0))
                open_val = float(first.get("y") or first.get("value") or first.get("last", 0))
            else:
                continue

            if current_val <= 0 or open_val <= 0:
                continue

            change = current_val - open_val
            change_pct = (change / open_val * 100) if open_val != 0 else 0

            result[src["name"]] = {
                "value": current_val,
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "description": src["description"],
                "ref_name": src["ref_name"],
            }
        except Exception as e:
            _log.debug("Weekend CFD fetch failed for %s: %s", src["name"], e)
            continue

    # フォールバック: yfinance のCFD先物から推定
    if not result:
        try:
            # ダウ先物 (YM=F) / 日経先物 (NKD=F) で代替
            for name, ticker, ref in [
                ("ダウ先物（参考）", "YM=F", "ダウ平均"),
                ("日経先物（参考）", "NKD=F", "日経平均"),
            ]:
                df = yf.download(ticker, period="5d", interval="1d",
                                 progress=False, auto_adjust=True)
                if df is not None and not df.empty and len(df) >= 2:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [str(c[0]).capitalize() for c in df.columns]
                    else:
                        df.columns = [str(c).capitalize() for c in df.columns]
                    if "Close" in df.columns:
                        last = float(df["Close"].iloc[-1])
                        prev = float(df["Close"].iloc[-2])
                        result[name] = {
                            "value": last,
                            "change": round(last - prev, 2),
                            "change_pct": round((last - prev) / prev * 100, 2),
                            "description": f"{ref}の先物。翌営業日の方向性を示唆",
                            "ref_name": ref,
                        }
        except Exception:
            pass

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

@st.cache_data(ttl=300)  # 5分キャッシュ（fetch_market_snapshot と同期）
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

    # ─── ウィークエンドCFD（サンデーダウ・日経）───────────────
    weekend = fetch_weekend_cfd()
    if weekend:
        lines.append("\n### ウィークエンドCFD（先物・先行指標）")
        for wname, wdata in weekend.items():
            val = f"{wdata['value']:,.0f}"
            ref = wdata.get("ref_name", "")
            # 金曜終値との乖離を計算
            ref_data = snapshot.get(ref)
            gap_text = ""
            if ref_data:
                gap = wdata["value"] - ref_data["value"]
                gap_pct = gap / ref_data["value"] * 100
                direction = "上昇示唆" if gap > 0 else "下落示唆"
                gap_text = f"  ※{ref}金曜終値比{gap_pct:+.2f}%（{direction}）"
            lines.append(
                f"- {wname}: {val}（変動{wdata['change_pct']:+.2f}%）{gap_text}"
                f"  ※{wdata['description']}"
            )

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

    # ─── マクロ経済指標（FRED）──────────────────────────────
    fred_data = fetch_fred_indicators()
    if fred_data:
        lines.append("\n### マクロ経済指標（FRED）")
        lines.append("※マクロ指標は月次/四半期発表のため、データ日付に注意。古いデータは参考程度に。")
        for name, info in fred_data.items():
            val = info["value"]
            unit = info.get("unit", "")
            desc = info.get("description", "")
            date = info.get("date", "")
            # データの経過日数を計算して鮮度を明示
            age_note = ""
            try:
                days_old = (pd.Timestamp.now() - pd.Timestamp(date)).days
                if days_old > 90:
                    age_note = f"（{days_old}日前のデータ、参考程度）"
                elif days_old > 30:
                    age_note = f"（{days_old}日前）"
            except Exception:
                pass
            lines.append(f"- {name}: {val}{unit}（{date}{age_note}）  ※{desc}")

    # ─── 分析ガイド ──────────────────────────────────────────
    lines.append(
        "\n上記のマーケット環境データをもとに、対象銘柄への影響を分析に必ず反映してください。"
        "例: VIX高水準→リスクオフ環境、逆イールド→景気後退リスク、"
        "円安→輸出企業に有利、金利上昇→グロース株に逆風、SOX好調→半導体関連に追い風、"
        "CPI上昇→利上げ懸念、PMI50割れ→景気縮小懸念、など。"
    )

    return "\n".join(lines)


# ─── FRED API（マクロ経済指標）──────────────────────────────────────

# (series_id, display_name, unit, description, transform)
# transform: "raw"=そのまま, "yoy_pct"=前年同月比%, "mom_pct"=前月比%
FRED_SERIES: list[tuple[str, str, str, str, str]] = [
    ("CPIAUCSL",         "CPI（総合）",           "",  "消費者物価指数。インフレの代表指標", "yoy_pct"),
    ("CPILFESL",         "CPI（コア）",           "",  "食品・エネルギー除く。FRBが重視", "yoy_pct"),
    ("PAYEMS",           "非農業部門雇用者数",     "千人", "雇用統計NFP。FRB政策に直結", "mom_diff"),
    ("UMCSENT",          "ミシガン大消費者信頼感", "",  "消費者心理。インフレ期待も含む", "raw"),
    ("A191RL1Q225SBEA",  "実質GDP成長率",         "%",  "四半期年率。2期連続マイナスで景気後退", "raw"),
    ("USSLIND",          "景気先行指数（LEI）",    "%",  "フィラデルフィア連銀。3ヶ月連続低下で警告", "raw"),
    ("BAMLH0A0HYM2",     "ハイイールドスプレッド", "%",  "ジャンク債と国債の利回り差。拡大=リスクオフ", "raw"),
    ("CSCICP03USM665S",  "消費者信頼感（OECD）",  "",   "OECD消費者信頼感指数。100超で楽観", "raw"),
]


@st.cache_data(ttl=3600 * 6)  # 6時間キャッシュ（マクロ指標は更新頻度が低い）
def fetch_fred_indicators() -> dict[str, dict]:
    """
    FRED API からマクロ経済指標の最新値を取得する。
    FRED_API_KEY が secrets に未設定の場合は空辞書を返す。
    """
    try:
        api_key = st.secrets.get("FRED_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key or len(api_key) < 10:
        return {}

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
    except Exception:
        return {}

    result: dict[str, dict] = {}

    for series_id, name, unit, desc, transform in FRED_SERIES:
        try:
            series = fred.get_series(series_id)
            if series is None or series.empty:
                continue

            series = series.dropna()
            if series.empty:
                continue

            latest_val = float(series.iloc[-1])
            latest_date = series.index[-1].strftime("%Y-%m-%d")

            if transform == "yoy_pct" and len(series) >= 13:
                # 前年同月比 %
                prev_year = float(series.iloc[-13])
                if prev_year != 0:
                    val = round((latest_val - prev_year) / prev_year * 100, 1)
                    result[name] = {
                        "value": val,
                        "unit": "%",
                        "description": desc,
                        "date": latest_date,
                        "series_id": series_id,
                    }
            elif transform == "mom_diff" and len(series) >= 2:
                # 前月差（千人）
                prev = float(series.iloc[-2])
                diff = round(latest_val - prev, 0)
                result[name] = {
                    "value": f"{diff:+,.0f}",
                    "unit": unit,
                    "description": desc,
                    "date": latest_date,
                    "series_id": series_id,
                    "raw_value": diff,
                }
            else:
                result[name] = {
                    "value": round(latest_val, 2) if abs(latest_val) < 1000 else round(latest_val, 0),
                    "unit": unit,
                    "description": desc,
                    "date": latest_date,
                    "series_id": series_id,
                }

        except Exception:
            continue

    return result


@st.cache_data(ttl=3600 * 12)
def fetch_cape_ratio() -> dict | None:
    """multpl.com から CAPEレシオ（シラーPER）を取得する。"""
    try:
        import requests
        from lxml import html as lhtml
        r = requests.get(
            "https://www.multpl.com/shiller-pe/table/by-month",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code != 200:
            return None
        tree = lhtml.fromstring(r.content)
        rows = tree.xpath('//table[@id="datatable"]//tr')
        if rows and len(rows) > 1:
            cells = rows[1].xpath(".//td")
            val = float(cells[1].text_content().strip())
            date = cells[0].text_content().strip()
            return {"value": val, "date": date}
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600 * 12)
def fetch_buffett_indicator() -> dict | None:
    """
    バフェット指標（株式時価総額 / GDP）を計算する。
    S&P 500 の時価総額を米国株式市場全体の代理として使用。
    """
    try:
        # S&P 500 の現在値から米国株式市場の時価総額を推定
        # S&P 500 ≈ 米国株式市場の約80%
        sp500 = yf.download("^GSPC", period="5d", progress=False)
        if sp500 is None or sp500.empty:
            return None
        sp500_val = float(sp500["Close"].iloc[-1])

        # FRED から GDP を取得
        try:
            api_key = st.secrets.get("FRED_API_KEY", "")
        except Exception:
            api_key = ""
        if not api_key:
            return None

        from fredapi import Fred
        fred = Fred(api_key=api_key)
        gdp = fred.get_series("GDP").dropna()
        gdp_val = float(gdp.iloc[-1])  # 十億ドル単位

        # Wilshire 5000（米国株式市場全体の時価総額）を直接取得
        try:
            wilshire = fred.get_series("WILL5000PR").dropna()
            if wilshire is not None and not wilshire.empty:
                # Wilshire 5000 index ≈ 米国株式市場時価総額（十億ドル）に近似
                # 2024年末基準: Wilshire 5000 ≈ 57000 → 時価総額≈57兆ドル
                wilshire_val = float(wilshire.iloc[-1])
                estimated_mktcap = wilshire_val  # 十億ドル近似
            else:
                # フォールバック: S&P500から推定
                estimated_mktcap = sp500_val / 6000 * 50000
        except Exception:
            estimated_mktcap = sp500_val / 6000 * 50000  # 十億ドル
        ratio = round(estimated_mktcap / gdp_val * 100, 1)

        return {
            "value": ratio,
            "date": gdp.index[-1].strftime("%Y-%m-%d"),
            "gdp": gdp_val,
        }
    except Exception:
        return None


@st.cache_data(ttl=3600 * 6)
def fetch_fred_series_history(series_id: str, periods: int = 60) -> pd.Series | None:
    """FRED の時系列データを取得（チャート用）。"""
    try:
        api_key = st.secrets.get("FRED_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key or len(api_key) < 10:
        return None

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
        series = fred.get_series(series_id)
        if series is not None and not series.empty:
            return series.dropna().tail(periods)
    except Exception:
        pass
    return None

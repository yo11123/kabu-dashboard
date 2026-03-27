"""
カスタムスクリーナー — ユーザー定義の条件で全銘柄をスキャン。
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import apply_theme
from modules.data_loader import load_tickers, load_all_tse_stocks

apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── スクリーニング関数 ───────────────────────────────────────────────────

def _calc_rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    loss = loss.replace(0, float("nan"))
    rsi = 100 - 100 / (1 + gain / loss)
    val = rsi.iloc[-1]
    return round(float(val), 1) if val == val else None


def _scan_stock(ticker: str, name: str, sector: str) -> dict | None:
    """1銘柄のスクリーニングデータを取得。"""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="6mo")
        if hist is None or len(hist) < 30:
            return None

        close = hist["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            return None

        # テクニカル
        rsi = _calc_rsi(close)

        sma25 = float(close.rolling(25).mean().iloc[-1]) if len(close) >= 25 else None
        sma75 = float(close.rolling(75).mean().iloc[-1]) if len(close) >= 75 else None

        # ボリンジャー
        bb_sigma = None
        if len(close) >= 20:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            if std20.iloc[-1] > 0:
                bb_sigma = round(float((price - sma20.iloc[-1]) / std20.iloc[-1]), 2)

        # 出来高比
        vol_ratio = None
        if len(hist) >= 30:
            v5 = hist["Volume"].iloc[-5:].mean()
            v30 = hist["Volume"].iloc[-30:].mean()
            if v30 > 0:
                vol_ratio = round(float(v5 / v30), 2)

        # MACD
        macd_hist = None
        if len(close) >= 35:
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal = macd_line.ewm(span=9).mean()
            macd_hist = round(float((macd_line - signal).iloc[-1]), 2)

        # リターン
        ret_1m = round(float((price / close.iloc[-22] - 1) * 100), 2) if len(close) >= 22 else None
        ret_3m = round(float((price / close.iloc[-66] - 1) * 100), 2) if len(close) >= 66 else None

        # ファンダメンタル
        per = info.get("trailingPE")
        pbr = info.get("priceToBook")
        div_yield_raw = info.get("dividendYield")
        # yfinance は通常 0.05 (=5%) だが、日本株で既に % 値 (5.0) が返る場合がある
        if div_yield_raw is not None:
            div_yield = div_yield_raw * 100 if div_yield_raw < 1 else div_yield_raw
            if div_yield > 30:  # 30% 超は異常値として除外
                div_yield = None
        else:
            div_yield = None
        roe = info.get("returnOnEquity")
        market_cap = info.get("marketCap")
        rev_growth = info.get("revenueGrowth")

        # 52週
        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")
        pct_from_high = round((price / high_52w - 1) * 100, 1) if high_52w else None
        pct_from_low = round((price / low_52w - 1) * 100, 1) if low_52w else None

        return {
            "code": ticker,
            "name": name,
            "sector": sector,
            "price": price,
            "rsi": rsi,
            "sma25": sma25,
            "sma75": sma75,
            "bb_sigma": bb_sigma,
            "vol_ratio": vol_ratio,
            "macd_hist": macd_hist,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "per": per,
            "pbr": pbr,
            "div_yield": div_yield,
            "roe": (roe * 100) if roe else None,
            "market_cap": market_cap,
            "rev_growth": (rev_growth * 100) if rev_growth else None,
            "pct_from_high": pct_from_high,
            "pct_from_low": pct_from_low,
        }
    except Exception:
        return None


@st.cache_data(ttl=14400, show_spinner=False)
def _scan_universe(tickers: tuple[tuple[str, str, str], ...]) -> list[dict]:
    """全銘柄をスキャンしてデータを取得。"""
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_scan_stock, t[0], t[1], t[2]): t[0]
            for t in tickers
        }
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
    return results


# ─── フィルタ条件定義 ─────────────────────────────────────────────────────

FILTER_FIELDS = {
    "PER": {"key": "per", "unit": "倍", "default_range": (0.0, 100.0), "step": 1.0},
    "PBR": {"key": "pbr", "unit": "倍", "default_range": (0.0, 10.0), "step": 0.1},
    "配当利回り": {"key": "div_yield", "unit": "%", "default_range": (0.0, 10.0), "step": 0.1},
    "ROE": {"key": "roe", "unit": "%", "default_range": (0.0, 50.0), "step": 1.0},
    "RSI": {"key": "rsi", "unit": "", "default_range": (0.0, 100.0), "step": 1.0},
    "BB σ": {"key": "bb_sigma", "unit": "σ", "default_range": (-3.0, 3.0), "step": 0.1},
    "出来高比": {"key": "vol_ratio", "unit": "倍", "default_range": (0.0, 5.0), "step": 0.1},
    "1ヶ月リターン": {"key": "ret_1m", "unit": "%", "default_range": (-50.0, 50.0), "step": 1.0},
    "3ヶ月リターン": {"key": "ret_3m", "unit": "%", "default_range": (-50.0, 50.0), "step": 1.0},
    "52週高値からの乖離": {"key": "pct_from_high", "unit": "%", "default_range": (-80.0, 0.0), "step": 1.0},
    "売上成長率": {"key": "rev_growth", "unit": "%", "default_range": (-50.0, 100.0), "step": 1.0},
}

# プリセット条件
PRESETS = {
    "バリュー株": [
        ("PER", "<=", 15.0),
        ("PBR", "<=", 1.0),
        ("配当利回り", ">=", 3.0),
    ],
    "割安成長株": [
        ("PER", "<=", 20.0),
        ("ROE", ">=", 10.0),
        ("売上成長率", ">=", 10.0),
    ],
    "テクニカル反発狙い": [
        ("RSI", "<=", 30.0),
        ("BB σ", "<=", -2.0),
        ("出来高比", ">=", 1.5),
    ],
    "高配当＋低PBR": [
        ("配当利回り", ">=", 4.0),
        ("PBR", "<=", 1.5),
    ],
    "モメンタム": [
        ("RSI", ">=", 50.0),
        ("1ヶ月リターン", ">=", 5.0),
        ("出来高比", ">=", 1.5),
    ],
}


def _apply_filters(data: list[dict], conditions: list[tuple]) -> list[dict]:
    """条件リストでフィルタリング。"""
    filtered = data
    for field_name, operator, value in conditions:
        field_info = FILTER_FIELDS.get(field_name)
        if not field_info:
            continue
        key = field_info["key"]

        def check(item, k=key, op=operator, v=value):
            val = item.get(k)
            if val is None:
                return False
            if op == "<=":
                return val <= v
            elif op == ">=":
                return val >= v
            elif op == "==":
                return val == v
            elif op == "<":
                return val < v
            elif op == ">":
                return val > v
            return True

        filtered = [item for item in filtered if check(item)]
    return filtered


# ─── メイン ───────────────────────────────────────────────────────────────

def main() -> None:
    st.title("🔍 カスタムスクリーナー")
    st.caption("ファンダメンタル + テクニカル条件を自由に組み合わせて銘柄をスキャン。プリセットも利用可能。")

    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()

    # ─── サイドバー ───────────────────────────────────────────────
    with st.sidebar:
        st.header("スキャン設定")

        # ユニバース選択
        prime = [t for t in all_tse if "プライム" in t.get("market", "")] if all_tse else []
        universe_opts = ["日経225"]
        if prime:
            universe_opts.append(f"東証プライム（{len(prime):,}銘柄）")
        if all_tse:
            universe_opts.append(f"東証全銘柄（{len(all_tse):,}銘柄）")

        universe = st.selectbox("スキャン対象", universe_opts)
        if "全銘柄" in universe:
            scan_stocks = all_tse
        elif "プライム" in universe:
            scan_stocks = prime
        else:
            scan_stocks = nikkei225

        st.divider()

        # プリセット or カスタム
        st.header("フィルタ条件")
        mode = st.radio("モード", ["プリセット", "カスタム"], horizontal=True)

        if mode == "プリセット":
            preset_name = st.selectbox("プリセット", list(PRESETS.keys()))
            conditions = PRESETS[preset_name]

            st.markdown("**適用条件:**")
            for field, op, val in conditions:
                unit = FILTER_FIELDS[field]["unit"]
                st.markdown(f"- {field} {op} {val}{unit}")

        else:
            # カスタム条件入力
            if "custom_conditions" not in st.session_state:
                st.session_state.custom_conditions = []

            # 条件追加
            field = st.selectbox("指標", list(FILTER_FIELDS.keys()), key="cs_field")
            operator = st.selectbox("条件", ["<=", ">=", "<", ">"], key="cs_op")
            field_info = FILTER_FIELDS[field]
            value = st.number_input(
                f"値 ({field_info['unit']})" if field_info["unit"] else "値",
                value=field_info["default_range"][1] / 2,
                step=field_info["step"],
                key="cs_value",
            )

            if st.button("条件を追加", use_container_width=True):
                st.session_state.custom_conditions.append((field, operator, value))
                st.rerun()

            # 現在の条件表示
            if st.session_state.custom_conditions:
                st.markdown("**現在の条件:**")
                for i, (f, o, v) in enumerate(st.session_state.custom_conditions):
                    unit = FILTER_FIELDS[f]["unit"]
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"- {f} {o} {v}{unit}")
                    if c2.button("✕", key=f"rm_cond_{i}"):
                        st.session_state.custom_conditions.pop(i)
                        st.rerun()

                if st.button("条件をクリア", use_container_width=True):
                    st.session_state.custom_conditions = []
                    st.rerun()

            conditions = st.session_state.custom_conditions

        st.divider()

        # ソート
        sort_field = st.selectbox(
            "ソート",
            ["配当利回り (高い順)", "PER (低い順)", "PBR (低い順)", "RSI (低い順)",
             "出来高比 (高い順)", "1ヶ月リターン (高い順)", "ROE (高い順)"],
        )

    # ─── スキャン実行 ─────────────────────────────────────────────
    if not conditions:
        st.info("サイドバーでフィルタ条件を設定してスキャンしてください。")
        st.stop()

    # 条件表示
    cond_text = " AND ".join(
        f"{f} {o} {v}{FILTER_FIELDS[f]['unit']}"
        for f, o, v in conditions
    )
    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.5); border: 1px solid rgba(212,175,55,0.08);
            border-left: 2px solid #d4af37; border-radius: 2px; padding: 14px 20px; margin-bottom: 16px;
        ">
            <span style="font-family:'Inter',sans-serif; font-size:0.7em; color:#d4af37;
                 letter-spacing:0.12em; text-transform:uppercase;">Filter Conditions</span>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.82em; color:#f0ece4; margin-top:6px;">
                {cond_text}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    tickers_tuple = tuple(
        (s["code"], s["name"], s.get("sector", ""))
        for s in scan_stocks
    )

    if len(scan_stocks) > 300:
        st.warning(f"⚠️ {len(scan_stocks):,} 銘柄のスキャンは初回 3〜5 分かかります（結果は4時間キャッシュ）。")

    with st.spinner(f"{len(scan_stocks):,} 銘柄をスキャン中..."):
        all_data = _scan_universe(tickers_tuple)

    # フィルタ適用
    filtered = _apply_filters(all_data, conditions)

    if not filtered:
        st.warning("条件に合致する銘柄がありませんでした。条件を緩めてみてください。")
        st.stop()

    # ソート
    sort_map = {
        "配当利回り (高い順)": ("div_yield", True),
        "PER (低い順)": ("per", False),
        "PBR (低い順)": ("pbr", False),
        "RSI (低い順)": ("rsi", False),
        "出来高比 (高い順)": ("vol_ratio", True),
        "1ヶ月リターン (高い順)": ("ret_1m", True),
        "ROE (高い順)": ("roe", True),
    }
    sort_key, sort_reverse = sort_map.get(sort_field, ("div_yield", True))
    filtered.sort(
        key=lambda x: x.get(sort_key) if x.get(sort_key) is not None else (-9999 if sort_reverse else 9999),
        reverse=sort_reverse,
    )

    st.subheader(f"スキャン結果: {len(filtered):,}銘柄 / {len(all_data):,}銘柄中")

    # テーブル表示
    display_data = []
    for item in filtered[:100]:
        row = {
            "コード": item["code"],
            "銘柄名": item["name"],
            "業種": item["sector"],
            "株価": f"¥{item['price']:,.0f}",
        }
        if item.get("per") is not None:
            row["PER"] = f"{item['per']:.1f}"
        if item.get("pbr") is not None:
            row["PBR"] = f"{item['pbr']:.2f}"
        if item.get("div_yield") is not None:
            row["配当利回り"] = f"{item['div_yield']:.2f}%"
        if item.get("roe") is not None:
            row["ROE"] = f"{item['roe']:.1f}%"
        if item.get("rsi") is not None:
            row["RSI"] = f"{item['rsi']:.0f}"
        if item.get("bb_sigma") is not None:
            row["BB σ"] = f"{item['bb_sigma']:.1f}"
        if item.get("vol_ratio") is not None:
            row["出来高比"] = f"{item['vol_ratio']:.1f}x"
        if item.get("ret_1m") is not None:
            row["1M"] = f"{item['ret_1m']:+.1f}%"
        display_data.append(row)

    df = pd.DataFrame(display_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 銘柄クリックでチャートへ
    st.divider()
    cols = st.columns(min(5, len(filtered[:20])))
    for i, item in enumerate(filtered[:20]):
        col = cols[i % len(cols)]
        if col.button(
            f"{item['name'][:6]}\n{item['code']}",
            key=f"cs_go_{i}",
            use_container_width=True,
        ):
            st.session_state["selected_ticker"] = item["code"]
            st.switch_page("pages/dashboard.py")


main()

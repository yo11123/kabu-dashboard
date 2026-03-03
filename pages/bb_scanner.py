import os

import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data_loader import load_all_tse_stocks, load_tickers
from modules.indicators import calc_bollinger_bands, calc_volume_ma
from modules.market_hours import market_status_label
from modules.styles import apply_theme

st.set_page_config(
    page_title="BBスキャナー | 日本株ダッシュボード",
    page_icon="📡",
    layout="wide",
)
apply_theme()

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")

# スキャン対象の上限（全銘柄は重いため警告を出す）
_LARGE_THRESHOLD = 500


# ─── ユーティリティ ──────────────────────────────────────────────────

def _count_walk_days(close: pd.Series, upper: pd.Series, threshold: float) -> int:
    """末尾から連続して BB 上限付近（Close >= Upper × threshold）だった日数を返す。"""
    count = 0
    for c, u in zip(close.iloc[::-1], upper.iloc[::-1]):
        if pd.isna(u) or pd.isna(c):
            break
        if c >= u * threshold:
            count += 1
        else:
            break
    return count


# ─── スキャン本体（1時間キャッシュ）────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _run_scan(
    ticker_codes: tuple,
    ticker_names: tuple,
    ticker_markets: tuple,
    bb_period: int,
    threshold: float,
    lookback: int,
) -> pd.DataFrame:
    """
    yfinance 一括ダウンロードで 3ヶ月分データを取得し、
    BB 2σ沿い上昇ブレイク銘柄をスクリーニングする。
    """
    name_map   = dict(zip(ticker_codes, ticker_names))
    market_map = dict(zip(ticker_codes, ticker_markets))
    min_bars   = bb_period + lookback + 5
    single     = len(ticker_codes) == 1

    try:
        raw = yf.download(
            tickers=list(ticker_codes),
            period="3mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        raise RuntimeError(f"yfinance ダウンロード失敗: {e}") from e

    results = []

    for code in ticker_codes:
        try:
            df = raw.copy() if single else raw[code].copy()

            if df is None or df.empty:
                continue

            # 列名正規化
            df.columns = [str(c).capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.dropna(subset=["Close"], inplace=True)

            if len(df) < min_bars:
                continue

            df = calc_bollinger_bands(df, period=bb_period)
            df = calc_volume_ma(df)
            df.dropna(subset=["BB_upper", "BB_middle", "BB_lower"], inplace=True)

            if len(df) < lookback + 2:
                continue

            latest = df.iloc[-1]

            # ── スクリーニング ──────────────────────────────────────
            # 1. 現在値が BB 上限付近
            if pd.isna(latest["BB_upper"]) or latest["Close"] < latest["BB_upper"] * threshold:
                continue

            # 2. BB 中心より上（上昇トレンド確認）
            if latest["Close"] <= latest["BB_middle"]:
                continue

            # 3. lookback 日前は BB 上限に達していなかった（新規性）
            prev = df.iloc[-(lookback + 1)]
            if not pd.isna(prev["BB_upper"]) and prev["Close"] >= prev["BB_upper"] * threshold:
                continue

            # ── メトリクス ─────────────────────────────────────────
            prev_close  = float(df.iloc[-2]["Close"]) if len(df) >= 2 else float(latest["Close"])
            change_pct  = (float(latest["Close"]) - prev_close) / prev_close * 100

            bb_width = float(latest["BB_upper"]) - float(latest["BB_lower"])
            bb_pos   = (float(latest["Close"]) - float(latest["BB_lower"])) / bb_width if bb_width > 0 else 0

            from_upper = (float(latest["Close"]) / float(latest["BB_upper"]) - 1) * 100

            # 出来高比（最新 / 25日MA）
            vol_ratio = None
            vol_ma_col = next((c for c in df.columns if c.startswith("Vol_M")), None)
            if vol_ma_col and float(latest[vol_ma_col]) > 0:
                vol_ratio = float(latest["Volume"]) / float(latest[vol_ma_col])

            walk_days = _count_walk_days(df["Close"].iloc[-20:], df["BB_upper"].iloc[-20:], threshold)

            results.append({
                "コード":    code,
                "銘柄名":    name_map.get(code, code),
                "市場":      market_map.get(code, ""),
                "現在値":    int(round(float(latest["Close"]))),
                "前日比%":   round(change_pct, 2),
                "BB上限":    int(round(float(latest["BB_upper"]))),
                "BB乖離%":   round(from_upper, 2),
                "継続日数":  walk_days,
                "BBポジション": round(bb_pos * 100, 1),
                "出来高比":  round(vol_ratio, 2) if vol_ratio is not None else None,
            })

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    df_result = pd.DataFrame(results)
    # 継続日数が少ない（新しいブレイク）順 → BBポジション高い順
    df_result = df_result.sort_values(
        ["継続日数", "BBポジション"],
        ascending=[True, False],
    ).reset_index(drop=True)
    return df_result


# ─── メイン ─────────────────────────────────────────────────────────

def main() -> None:
    st.title("📡 BBスキャナー — 2σライン沿い 上昇ブレイク銘柄")

    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, tse_error = load_all_tse_stocks()

    prime_stocks    = [t for t in all_tse if "プライム" in t.get("market", "")] if all_tse else []
    standard_stocks = [t for t in all_tse if "スタンダード" in t.get("market", "")] if all_tse else []

    # ─── サイドバー ───────────────────────────────────────────────────
    with st.sidebar:
        st.header("スキャン設定")

        universe_options = ["日経225"]
        if prime_stocks:
            universe_options.append(f"東証プライム（{len(prime_stocks):,}銘柄）")
        if standard_stocks:
            universe_options.append(f"東証スタンダード（{len(standard_stocks):,}銘柄）")
        if all_tse:
            universe_options.append(f"東証全銘柄（{len(all_tse):,}銘柄）")

        universe_choice = st.selectbox("スキャン対象", universe_options)

        if "プライム" in universe_choice:
            scan_items = prime_stocks
        elif "スタンダード" in universe_choice:
            scan_items = standard_stocks
        elif "全銘柄" in universe_choice:
            scan_items = all_tse
        else:
            scan_items = nikkei225

        if len(scan_items) > _LARGE_THRESHOLD:
            st.warning(
                f"⚠️ {len(scan_items):,} 銘柄のスキャンは初回 3〜5 分かかります。"
                "結果は 1 時間キャッシュされます。"
            )

        st.divider()
        st.subheader("BB パラメータ")
        bb_period = st.slider("BB 期間（日）", 10, 30, 20, step=1)
        threshold_pct = st.slider(
            "上限到達判定（%）",
            90, 100, 97, step=1,
            help="終値が BB 上限の何 % 以上なら「上限付近」とみなすか",
        )
        lookback = st.slider(
            "新規性チェック（日前）",
            3, 15, 5, step=1,
            help="この日数前は BB 上限に達していなかった銘柄のみヒット",
        )

        st.divider()
        st.caption(market_status_label())
        scan_btn = st.button("🔍 スキャン開始", type="primary", use_container_width=True)

    # ─── スキャン実行 ────────────────────────────────────────────────
    if scan_btn:
        ticker_codes   = tuple(t["code"] for t in scan_items)
        ticker_names   = tuple(t.get("name", "") for t in scan_items)
        ticker_markets = tuple(t.get("market", "") for t in scan_items)

        with st.spinner(
            f"{len(scan_items):,} 銘柄をスキャン中…"
            "（初回は数十秒〜数分かかります）"
        ):
            try:
                results = _run_scan(
                    ticker_codes, ticker_names, ticker_markets,
                    bb_period, threshold_pct / 100, lookback,
                )
                st.session_state["bb_scan_results"] = results
                st.session_state["bb_scan_meta"] = {
                    "universe": universe_choice.split("（")[0],
                    "total":    len(scan_items),
                    "bb_period": bb_period,
                    "threshold": threshold_pct,
                    "lookback":  lookback,
                }
            except Exception as e:
                st.error(f"スキャン失敗: {e}")
                return

    # ─── 結果表示 ────────────────────────────────────────────────────
    results: pd.DataFrame | None = st.session_state.get("bb_scan_results")
    meta: dict = st.session_state.get("bb_scan_meta", {})

    if results is None:
        # 初回説明
        st.info("サイドバーの **「スキャン開始」** を押してください。")
        with st.expander("スクリーニング条件の説明", expanded=True):
            st.markdown("""
| 条件 | 内容 |
|------|------|
| **① BB 上限到達** | 終値 ≥ BB 上限（2σ）× 判定 % |
| **② 上昇トレンド** | 終値 > BB 中心（20 日移動平均）|
| **③ 新規ブレイク** | N 日前は BB 上限に達していなかった |

**継続日数**（少ない = 新しいブレイク）で昇順ソートし、
最もフレッシュなブレイクアウト銘柄が上に来ます。
            """)
        return

    if results.empty:
        st.warning("条件に合致する銘柄が見つかりませんでした。閾値を下げるか、対象銘柄を広げてみてください。")
        return

    # ── サマリ ─────────────────────────────────────────────────────
    hit = len(results)
    total = meta.get("total", 0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ヒット銘柄数", f"{hit} 件", f"/ {total:,} 銘柄")
    c2.metric("BB 期間", f"{meta.get('bb_period', 20)} 日")
    c3.metric("上限判定", f"{meta.get('threshold', 97)} %")
    c4.metric("新規性チェック", f"{meta.get('lookback', 5)} 日前")

    st.caption(
        f"**{meta.get('universe', '')}** のうち BB 2σ 上限を"
        f"直近 {meta.get('lookback', 5)} 日以内にブレイクした銘柄 — "
        "継続日数（少）→ BBポジション（高）順"
    )

    st.divider()

    # ── 結果テーブル ───────────────────────────────────────────────
    display_df = results.drop(columns=["BBポジション"], errors="ignore")

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "コード":    st.column_config.TextColumn("コード",    width="small"),
            "銘柄名":    st.column_config.TextColumn("銘柄名",    width="medium"),
            "市場":      st.column_config.TextColumn("市場",      width="small"),
            "現在値":    st.column_config.NumberColumn("現在値",   format="¥%d"),
            "前日比%":   st.column_config.NumberColumn("前日比%",  format="%.2f%%"),
            "BB上限":    st.column_config.NumberColumn("BB 上限",  format="¥%d"),
            "BB乖離%":   st.column_config.NumberColumn("BB 乖離%", format="%.2f%%",
                         help="現在値が BB 上限を何 % 上回っているか（+ は上方突破）"),
            "継続日数":  st.column_config.NumberColumn("継続日数", format="%d 日",
                         help="BB 上限付近に連続して滞在している日数（1 日 = 今日ブレイク）"),
            "出来高比":  st.column_config.NumberColumn("出来高比", format="%.2f ×",
                         help="直近出来高 / 25 日平均出来高"),
        },
        hide_index=True,
    )

    # ── チャート確認ナビ ───────────────────────────────────────────
    st.divider()
    st.subheader("チャートで詳細確認")

    code_options = results["コード"].tolist()
    label_map    = {
        row["コード"]: f"{row['コード']}  {row['銘柄名']}"
        for _, row in results.iterrows()
    }

    col_sel, col_btn = st.columns([4, 1])
    selected_code = col_sel.selectbox(
        "銘柄を選択",
        options=code_options,
        format_func=lambda c: label_map.get(c, c),
        label_visibility="collapsed",
    )
    if col_btn.button("📊 表示", type="primary", use_container_width=True):
        st.session_state["calendar_selected_ticker"] = selected_code
        st.switch_page("app.py")


if __name__ == "__main__":
    main()

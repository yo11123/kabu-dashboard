import os

import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data_loader import load_all_tse_stocks, load_tickers
from modules.indicators import calc_bollinger_bands, calc_volume_ma
from modules.market_hours import market_status_label
from modules.styles import apply_theme
try:
    from modules.lstm_predictor import is_model_available, predict_proba as _lstm_predict
except ImportError:
    def is_model_available() -> bool:
        return False
    def _lstm_predict(*_a, **_kw):
        return None

from modules.loading import helix_spinner
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
    「上昇中の BB +2σ に沿って上がり始めた」銘柄をスクリーニングする。

    スクリーニング条件（全て AND）:
      1. 現在値 >= BB上限 × threshold（上限ライン付近）
      2. BB上限自体が右肩上がり（バンドが上昇中）
      3. BB中心（移動平均）も上昇中（上昇トレンド確認）
      4. バンド幅が拡大中（モメンタム増加）
      5. lookback 日前は上限に達していなかった（新規ブレイク）
      6. 出来高が平均以上（ブレイクアウトの裏付け）
    """
    name_map   = dict(zip(ticker_codes, ticker_names))
    market_map = dict(zip(ticker_codes, ticker_markets))
    min_bars   = bb_period + max(lookback, 10) + 5
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

            n = len(df)
            if n < 12:
                continue

            # インデックス参照用スナップショット
            p0 = df.iloc[-1]   # 現在
            p3 = df.iloc[-4]   # 3営業日前
            p6 = df.iloc[-7]   # 6営業日前（存在チェック済み: n>=12）

            # ── 条件1: 現在値が BB 上限付近 ──────────────────────────
            if pd.isna(p0["BB_upper"]) or p0["Close"] < p0["BB_upper"] * threshold:
                continue

            # ── 条件2: BB 上限自体が右肩上がり ───────────────────────
            # 「3日前より高く、6日前より高い」＝ 連続的に上昇中
            if not (p0["BB_upper"] > p3["BB_upper"] > p6["BB_upper"]):
                continue

            # ── 条件3: BB 中心（移動平均）も上昇中 ───────────────────
            if not (p0["BB_middle"] > p3["BB_middle"] > p6["BB_middle"]):
                continue

            # ── 条件4: バンド幅が拡大中（モメンタム増加）────────────
            bw_now  = float(p0["BB_upper"]) - float(p0["BB_lower"])
            bw_prev = float(p6["BB_upper"]) - float(p6["BB_lower"])
            if bw_now <= bw_prev:
                continue

            # ── 条件5: lookback 日前は上限に未達（新規ブレイク）─────
            if n > lookback + 1:
                px = df.iloc[-(lookback + 1)]
                if not pd.isna(px["BB_upper"]) and px["Close"] >= px["BB_upper"] * threshold:
                    continue

            # ── 条件6: 出来高が平均以上（ブレイクの裏付け）──────────
            vol_ma_col = next((c for c in df.columns if c.startswith("Vol_M")), None)
            vol_ratio = None
            if vol_ma_col:
                vma = float(p0[vol_ma_col])
                if vma > 0:
                    vol_ratio = float(p0["Volume"]) / vma
                    if vol_ratio < 0.8:   # 出来高が平均の 80% 未満は除外
                        continue

            # ── メトリクス計算 ────────────────────────────────────────
            prev_close = float(df.iloc[-2]["Close"]) if n >= 2 else float(p0["Close"])
            change_pct = (float(p0["Close"]) - prev_close) / prev_close * 100

            bb_width = float(p0["BB_upper"]) - float(p0["BB_lower"])
            bb_pos   = (float(p0["Close"]) - float(p0["BB_lower"])) / bb_width if bb_width > 0 else 0
            from_upper = (float(p0["Close"]) / float(p0["BB_upper"]) - 1) * 100

            # BB 上限の 5 営業日傾き（%/日）
            if n >= 6:
                bb_slope_pct = (float(p0["BB_upper"]) - float(p6["BB_upper"])) \
                               / float(p6["BB_upper"]) * 100
            else:
                bb_slope_pct = 0.0

            walk_days = _count_walk_days(
                df["Close"].iloc[-20:], df["BB_upper"].iloc[-20:], threshold
            )

            # ── AI 成功確率（モデルが存在する場合のみ）────────────────────
            ai_prob = _lstm_predict(df) if is_model_available() else None

            results.append({
                "コード":      code,
                "銘柄名":      name_map.get(code, code),
                "市場":        market_map.get(code, ""),
                "現在値":      int(round(float(p0["Close"]))),
                "前日比%":     round(change_pct, 2),
                "BB上限":      int(round(float(p0["BB_upper"]))),
                "BB乖離%":     round(from_upper, 2),
                "BB上昇率%":   round(bb_slope_pct, 2),
                "継続日数":    walk_days,
                "BBポジション": round(bb_pos * 100, 1),
                "出来高比":    round(vol_ratio, 2) if vol_ratio is not None else None,
                "AI確率%":     ai_prob,
            })

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    df_result = pd.DataFrame(results)
    # BB 上昇率が高く、かつ継続日数が少ない（新しいブレイク）順
    df_result = df_result.sort_values(
        ["継続日数", "BB上昇率%"],
        ascending=[True, False],
    ).reset_index(drop=True)
    return df_result


# ─── メイン ─────────────────────────────────────────────────────────

def main() -> None:
    st.markdown("<h1 style='font-family:Cormorant Garamond,serif; font-weight:300; letter-spacing:0.12em; font-size:1.6rem;'>BBスキャナー — 2σライン沿い 上昇ブレイク銘柄</h1>", unsafe_allow_html=True)

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

        with helix_spinner(
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
| **① 現在値が上限付近** | 終値 ≥ BB 上限（2σ）× 判定 % |
| **② BB 上限が右肩上がり** | 現在 > 3日前 > 6日前（バンド自体が上昇中）|
| **③ BB 中心も上昇中** | 移動平均が 3日・6日前より高い（上昇トレンド確認）|
| **④ バンド幅が拡大中** | 現在の幅 > 6日前の幅（モメンタム増加）|
| **⑤ 新規ブレイク** | N 日前は BB 上限に未達（ずっと居座っている銘柄を除外）|
| **⑥ 出来高裏付け** | 直近出来高 ≥ 25日平均の 80%（空振りブレイクを除外）|

**BB 上昇率%**（高い）→ **継続日数**（少ない）順でソートし、
勢いが強く、かつ最もフレッシュなブレイクアウト銘柄が上に来ます。
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
        f"**{meta.get('universe', '')}** のうち「上昇中 BB +2σ に沿って"
        f"直近 {meta.get('lookback', 5)} 日以内にブレイクした」銘柄 — "
        "継続日数（少）→ BB上昇率（高）順"
    )

    st.divider()

    # ── 結果テーブル ───────────────────────────────────────────────
    display_df = results.drop(columns=["BBポジション"], errors="ignore")

    # AI モデル未学習の場合は列ごと非表示
    if "AI確率%" in display_df.columns and display_df["AI確率%"].isna().all():
        display_df = display_df.drop(columns=["AI確率%"])

    col_config = {
        "コード":     st.column_config.TextColumn("コード",     width="small"),
        "銘柄名":     st.column_config.TextColumn("銘柄名",     width="medium"),
        "市場":       st.column_config.TextColumn("市場",       width="small"),
        "現在値":     st.column_config.NumberColumn("現在値",    format="¥%d"),
        "前日比%":    st.column_config.NumberColumn("前日比%",   format="%.2f%%"),
        "BB上限":     st.column_config.NumberColumn("BB 上限",   format="¥%d"),
        "BB乖離%":    st.column_config.NumberColumn("BB 乖離%",  format="%.2f%%",
                      help="現在値が BB 上限を何 % 上回っているか（+ は上方突破）"),
        "BB上昇率%":  st.column_config.NumberColumn("BB 上昇率%", format="%.2f%%",
                      help="6営業日前と比べた BB 上限の上昇率（高いほど勢いが強い）"),
        "継続日数":   st.column_config.NumberColumn("継続日数",  format="%d 日",
                      help="BB 上限付近に連続して滞在している日数（1 日 = 今日ブレイク）"),
        "出来高比":   st.column_config.NumberColumn("出来高比",  format="%.2f ×",
                      help="直近出来高 / 25 日平均出来高"),
        "AI確率%":    st.column_config.ProgressColumn(
                          "AI確率%",
                          format="%.1f%%",
                          min_value=0,
                          max_value=100,
                          help="LSTM が予測する「10営業日以内に +5% 上昇」の確率（train_lstm.ipynb で学習後に有効）",
                      ),
    }

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config=col_config,
        hide_index=True,
    )

    if not is_model_available():
        st.caption(
            "💡 **AI確率%** 列は `train_lstm.ipynb` で学習後、"
            "`models/lstm_bb.pt` と `models/scaler_bb.pkl` を commit すると表示されます。"
        )

    # ── チャート確認ナビ（銘柄ごとにボタンを配置）──────────────────
    st.divider()
    st.subheader("チャートで詳細確認")
    st.caption("ボタンをクリックするとメインチャートに移動します。")

    COLS = 4
    for chunk_start in range(0, len(results), COLS):
        chunk = results.iloc[chunk_start : chunk_start + COLS]
        btn_cols = st.columns(COLS)
        for col_idx, (_, row) in enumerate(chunk.iterrows()):
            change_sign = "▲" if row["前日比%"] >= 0 else "▼"
            btn_label = (
                f"**{row['コード']}**  {row['銘柄名']}  \n"
                f"¥{row['現在値']:,}  {change_sign}{abs(row['前日比%']):.2f}%"
            )
            with btn_cols[col_idx]:
                if st.button(
                    btn_label,
                    key=f"nav_{row['コード']}",
                    use_container_width=True,
                    help=(
                        f"継続 {row['継続日数']} 日　"
                        f"BB 乖離 {row['BB乖離%']:+.2f}%　"
                        f"出来高比 {row['出来高比'] or '-'}×"
                    ),
                ):
                    st.session_state["calendar_selected_ticker"] = row["コード"]
                    st.switch_page("views/dashboard.py")


if __name__ == "__main__":
    main()

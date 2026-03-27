"""
バックテスト — 売買戦略を過去データで検証し、AIが最適戦略を提案。
"""
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import (
    apply_theme, BG_BASE, BG_PANEL, TEXT_MUTED, TEXT_PRIMARY, GRID_COLOR,
    ACCENT, UP_COLOR, DOWN_COLOR,
)
from modules.data_loader import load_tickers, load_all_tse_stocks

from modules.loading import helix_spinner
apply_theme()

from modules.backtest import (
    PRESET_STRATEGIES,
    prepare_backtest_data,
    run_backtest,
)

TICKERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikkei225_tickers.txt")


# ─── チャート ─────────────────────────────────────────────────────────────

def _equity_chart(result: dict, ticker: str) -> go.Figure:
    """資産推移チャート。"""
    eq = result["equity_curve"]
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=eq.index, y=eq.values,
        mode="lines",
        name="戦略",
        line=dict(color=ACCENT, width=2),
        fill="tozeroy",
        fillcolor="rgba(212,175,55,0.05)",
    ))

    # バイ&ホールド
    bh = result.get("buy_and_hold_curve")
    if bh is not None:
        fig.add_trace(go.Scatter(
            x=bh.index, y=bh.values,
            mode="lines",
            name="バイ＆ホールド",
            line=dict(color=TEXT_MUTED, width=1, dash="dot"),
        ))

    # 売買ポイント
    for trade in result.get("trades", []):
        fig.add_trace(go.Scatter(
            x=[trade["entry_date"]],
            y=[eq.get(trade["entry_date"], trade["entry_price"])],
            mode="markers",
            marker=dict(color=UP_COLOR, size=8, symbol="triangle-up"),
            name="買い",
            showlegend=False,
        ))
        if trade.get("exit_date"):
            fig.add_trace(go.Scatter(
                x=[trade["exit_date"]],
                y=[eq.get(trade["exit_date"], trade["exit_price"])],
                mode="markers",
                marker=dict(color=DOWN_COLOR, size=8, symbol="triangle-down"),
                name="売り",
                showlegend=False,
            ))

    fig.update_layout(
        title=dict(
            text=f"{ticker} 資産推移",
            font=dict(family="'Inter', sans-serif", size=14, color=ACCENT),
        ),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=11),
        margin=dict(l=60, r=20, t=50, b=40),
        height=400,
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR,
                   tickformat="%Y/%m/%d" if len(eq) <= 90 else "%Y/%m"),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, title="評価額 (¥)"),
        legend=dict(orientation="h", y=1.05),
    )
    return fig


# ─── AI戦略提案 ───────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def _ai_strategy_suggestion(
    ticker: str,
    company_name: str,
    backtest_results_json: str,
    api_key: str,
) -> dict:
    """AIが最適戦略を提案する。"""
    from modules.ai_analysis import call_light_llm, _parse_json, _classify_error

    prompt = f"""あなたは定量的投資戦略の専門家です。
以下の銘柄の過去バックテスト結果を分析し、この銘柄に最も適した売買戦略を提案してください。

## 銘柄
{company_name} ({ticker})

## バックテスト結果（複数戦略）
{backtest_results_json}

## 分析と提案
1. 各戦略の成績を比較し、この銘柄の値動きの特性を分析
2. この銘柄に最も適した戦略とその理由を説明
3. カスタム戦略の具体的なパラメータを提案
4. リスク管理のアドバイス

## 出力形式（JSON のみ）
```json
{{
  "best_strategy": "最適戦略名",
  "best_reason": "推奨理由（3〜4文）",
  "stock_characteristics": "この銘柄の値動きの特性（2〜3文）",
  "custom_suggestion": {{
    "description": "カスタム戦略の説明",
    "buy_condition": "買い条件（具体的に）",
    "sell_condition": "売り条件（具体的に）",
    "expected_advantage": "この戦略の優位性"
  }},
  "risk_advice": "リスク管理のアドバイス（2〜3文）",
  "parameter_tuning": ["パラメータ調整の提案1", "提案2"]
}}
```"""

    try:
        text = call_light_llm(prompt)
        return {**_parse_json(text), "error": False}
    except Exception as e:
        return {
            "best_strategy": "",
            "best_reason": _classify_error(str(e), "gemini"),
            "error": True,
        }


# ─── メイン ───────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown("<h1 style='font-family:Cormorant Garamond,serif; font-weight:300; letter-spacing:0.12em; font-size:1.6rem;'>バックテスト</h1>", unsafe_allow_html=True)
    st.caption(
        "売買戦略を過去データで検証。プリセット戦略の比較や、"
        "AIによる最適戦略の提案が受けられます。"
    )

    nikkei225 = load_tickers(TICKERS_PATH)
    all_tse, _ = load_all_tse_stocks()
    all_stocks = all_tse if all_tse else nikkei225
    stock_map = {s["code"]: s["name"] for s in all_stocks}

    # ─── サイドバー ───────────────────────────────────────────────
    with st.sidebar:
        st.header("バックテスト設定")

        # 銘柄選択
        search = st.text_input("銘柄検索", placeholder="コード or 名前", key="bt_search")
        if search:
            matches = [
                s for s in all_stocks
                if search.lower() in s["code"].lower()
                or search.lower() in s["name"].lower()
            ][:20]
            if matches:
                options = [f"{s['code']} {s['name']}" for s in matches]
                selected = st.selectbox("候補", options, key="bt_select")
                ticker = selected.split(" ")[0]
            else:
                ticker = search.strip()
                if not ticker.endswith(".T"):
                    ticker = f"{ticker}.T"
        else:
            ticker = st.text_input("銘柄コード", value="7203.T", key="bt_ticker")

        # 期間
        period = st.selectbox("テスト期間", ["1年", "2年", "3年", "5年"], index=1, key="bt_period")
        period_map = {"1年": "1y", "2年": "2y", "3年": "3y", "5年": "5y"}

        # 初期資金
        capital = st.number_input("初期資金 (¥)", value=1_000_000, step=100_000, key="bt_capital")

        st.divider()

        # 戦略選択
        st.header("戦略")
        strategy_mode = st.radio("モード", ["プリセット", "全戦略比較", "AI提案"], key="bt_mode")

        if strategy_mode == "プリセット":
            strat_name = st.selectbox("戦略", list(PRESET_STRATEGIES.keys()), key="bt_strat")
            st.markdown(f"*{PRESET_STRATEGIES[strat_name]['description']}*")

        if strategy_mode == "AI提案":
            try:
                api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
            except Exception:
                api_key = ""
            if not api_key:
                api_key = st.text_input("APIキー", type="password", key="bt_api_key")

    # ─── バックテスト実行 ─────────────────────────────────────────
    company_name = stock_map.get(ticker, ticker)

    with helix_spinner(f"{company_name} のデータを取得中..."):
        try:
            df = yf.Ticker(ticker).history(period=period_map[period], interval="1d")
            if df.empty:
                st.error(f"{ticker} のデータを取得できませんでした。")
                st.stop()
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
            st.stop()

    bt_df = prepare_backtest_data(df)

    if strategy_mode == "プリセット":
        # 単一戦略のバックテスト
        strat = PRESET_STRATEGIES[strat_name]
        result = run_backtest(bt_df, strat["buy_condition"], strat["sell_condition"], capital)

        # 結果表示
        st.subheader(f"{strat_name}: {strat['description']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("総リターン", f"{result['total_return']:+.1f}%")
        c2.metric("勝率", f"{result['win_rate']:.0f}%")
        c3.metric("最大DD", f"{result['max_drawdown']:.1f}%")
        c4.metric("取引回数", f"{result['num_trades']}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("シャープレシオ", f"{result['sharpe_ratio']:.2f}")
        c6.metric("プロフィットファクター", f"{result['profit_factor']:.2f}")
        c7.metric("平均保有日数", f"{result['avg_holding_days']:.0f}日")
        c8.metric("B&H比較", f"{result['total_return'] - result['buy_and_hold_return']:+.1f}%pt")

        fig = _equity_chart(result, ticker)
        st.plotly_chart(fig, use_container_width=True)

        # 取引履歴
        if result["trades"]:
            with st.expander(f"取引履歴（{len(result['trades'])}件）"):
                trade_data = []
                for t in result["trades"]:
                    trade_data.append({
                        "買い日": t["entry_date"].strftime("%Y-%m-%d") if hasattr(t["entry_date"], "strftime") else str(t["entry_date"]),
                        "売り日": t["exit_date"].strftime("%Y-%m-%d") if t.get("exit_date") and hasattr(t["exit_date"], "strftime") else str(t.get("exit_date", "")),
                        "買値": f"¥{t['entry_price']:,.0f}",
                        "売値": f"¥{t['exit_price']:,.0f}" if t.get("exit_price") else "",
                        "リターン": f"{t['return_pct']:+.1f}%",
                        "日数": f"{t['holding_days']}",
                    })
                st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

    elif strategy_mode == "全戦略比較":
        st.subheader("全戦略比較")
        results_all = {}

        progress = st.progress(0)
        strats = list(PRESET_STRATEGIES.items())

        for i, (name, strat) in enumerate(strats):
            progress.progress((i + 1) / len(strats), text=f"{name} をテスト中...")
            result = run_backtest(bt_df, strat["buy_condition"], strat["sell_condition"], capital)
            results_all[name] = result

        progress.empty()

        # 比較テーブル
        compare_data = []
        for name, result in results_all.items():
            compare_data.append({
                "戦略": name,
                "総リターン": f"{result['total_return']:+.1f}%",
                "勝率": f"{result['win_rate']:.0f}%",
                "最大DD": f"{result['max_drawdown']:.1f}%",
                "シャープ": f"{result['sharpe_ratio']:.2f}",
                "PF": f"{result['profit_factor']:.2f}",
                "取引数": result["num_trades"],
                "vs B&H": f"{result['total_return'] - result['buy_and_hold_return']:+.1f}%pt",
            })

        st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)

        # 全戦略の資産推移を重ねたチャート
        fig = go.Figure()
        for name, result in results_all.items():
            eq = result["equity_curve"]
            fig.add_trace(go.Scatter(
                x=eq.index, y=eq.values,
                mode="lines", name=name,
                line=dict(width=1.5),
            ))

        fig.update_layout(
            title=dict(text="戦略別資産推移", font=dict(family="'Inter', sans-serif", size=14, color=ACCENT)),
            plot_bgcolor=BG_BASE,
            paper_bgcolor=BG_PANEL,
            font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=11),
            margin=dict(l=60, r=20, t=50, b=40),
            height=450,
            xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickformat="%Y/%m"),
            yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, title="評価額 (¥)"),
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig, use_container_width=True)

    elif strategy_mode == "AI提案":
        from modules.ai_analysis import get_light_llm_provider
        st.subheader("AI戦略提案")
        st.caption(f"Powered by {get_light_llm_provider()}")

        if not api_key:
            st.warning("APIキーを入力してください。")
            st.stop()

        # まず全戦略をバックテスト
        with helix_spinner("全戦略をバックテスト中..."):
            results_all = {}
            for name, strat in PRESET_STRATEGIES.items():
                result = run_backtest(bt_df, strat["buy_condition"], strat["sell_condition"], capital)
                results_all[name] = {
                    "total_return": result["total_return"],
                    "win_rate": result["win_rate"],
                    "max_drawdown": result["max_drawdown"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "profit_factor": result["profit_factor"],
                    "num_trades": result["num_trades"],
                    "buy_and_hold_return": result["buy_and_hold_return"],
                }

        with helix_spinner("AIが最適戦略を分析中..."):
            ai_result = _ai_strategy_suggestion(
                ticker=ticker,
                company_name=company_name,
                backtest_results_json=json.dumps(results_all, ensure_ascii=False, indent=2),
                api_key=api_key,
            )

        if ai_result.get("error"):
            st.error(ai_result.get("best_reason", "AI分析エラー"))
        else:
            st.markdown(
                f"""<div style="
                    background: rgba(10,15,26,0.5); border: 1px solid rgba(212,175,55,0.08);
                    border-left: 2px solid #d4af37; border-radius: 2px; padding: 20px 28px;
                ">
                    <span style="font-family:'Inter',sans-serif; font-size:0.65em; color:#d4af37;
                         letter-spacing:0.15em; text-transform:uppercase;">AI Recommended Strategy</span>
                    <div style="font-family:'Cormorant Garamond',serif; font-size:1.4em; color:#f0ece4;
                         margin-top:4px; letter-spacing:0.04em;">
                        {ai_result.get('best_strategy', '')}
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

            if ai_result.get("best_reason"):
                st.markdown(f"\n{ai_result['best_reason']}")

            if ai_result.get("stock_characteristics"):
                st.markdown(f"**銘柄の値動き特性**\n\n{ai_result['stock_characteristics']}")

            custom = ai_result.get("custom_suggestion", {})
            if custom:
                st.divider()
                st.markdown("**カスタム戦略の提案**")
                st.markdown(f"- **概要**: {custom.get('description', '')}")
                st.markdown(f"- **買い条件**: {custom.get('buy_condition', '')}")
                st.markdown(f"- **売り条件**: {custom.get('sell_condition', '')}")
                st.markdown(f"- **優位性**: {custom.get('expected_advantage', '')}")

            if ai_result.get("risk_advice"):
                st.markdown(f"\n**リスク管理**\n\n{ai_result['risk_advice']}")

            if ai_result.get("parameter_tuning"):
                st.markdown("**パラメータ調整の提案**")
                for p in ai_result["parameter_tuning"]:
                    st.markdown(f"- {p}")


main()

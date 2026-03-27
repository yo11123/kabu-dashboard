"""
セクター分析 — セクターローテーション、資金フロー、月別リターン可視化。
"""
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.styles import (
    apply_theme, BG_BASE, BG_PANEL, TEXT_MUTED, TEXT_PRIMARY, GRID_COLOR,
    ACCENT, UP_COLOR, DOWN_COLOR,
)

apply_theme()

from modules.sector_analysis import (
    fetch_sector_performance,
    calc_fund_flow,
    detect_sector_rotation,
    get_cycle_sector_map,
    calc_monthly_sector_returns,
)


# ─── チャート作成ヘルパー ─────────────────────────────────────────────────

def _make_bar_chart(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    """横棒グラフを作成。"""
    df_sorted = df.sort_values(col, ascending=True)
    colors = [UP_COLOR if v >= 0 else DOWN_COLOR for v in df_sorted[col]]

    fig = go.Figure(go.Bar(
        x=df_sorted[col],
        y=df_sorted["sector"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df_sorted[col]],
        textposition="outside",
        textfont=dict(size=11, color=TEXT_PRIMARY),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="'Inter', sans-serif", size=14, color=ACCENT)),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=11),
        margin=dict(l=120, r=60, t=50, b=30),
        height=max(400, len(df_sorted) * 32),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=True, zerolinecolor=TEXT_MUTED),
        yaxis=dict(showgrid=False),
    )
    return fig


def _make_heatmap(df: pd.DataFrame, title: str) -> go.Figure:
    """月別セクターリターンのヒートマップ。"""
    fig = go.Figure(go.Heatmap(
        z=df.values,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=[
            [0, DOWN_COLOR],
            [0.5, BG_PANEL],
            [1, UP_COLOR],
        ],
        zmid=0,
        text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in df.values],
        texttemplate="%{text}",
        textfont=dict(size=10),
        hovertemplate="セクター: %{y}<br>月: %{x}<br>リターン: %{z:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="'Inter', sans-serif", size=14, color=ACCENT)),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=11),
        margin=dict(l=120, r=20, t=50, b=40),
        height=max(400, len(df) * 35),
        xaxis=dict(side="top"),
    )
    return fig


def _make_fund_flow_chart(df: pd.DataFrame) -> go.Figure:
    """資金フローの横棒グラフ。"""
    df_sorted = df.sort_values("fund_flow", ascending=True)
    colors = [UP_COLOR if v >= 0 else DOWN_COLOR for v in df_sorted["fund_flow"]]

    fig = go.Figure(go.Bar(
        x=df_sorted["fund_flow"],
        y=df_sorted["sector"],
        orientation="h",
        marker_color=colors,
        text=[d for d in df_sorted["flow_direction"]],
        textposition="outside",
        textfont=dict(size=11, color=TEXT_PRIMARY),
    ))
    fig.update_layout(
        title=dict(
            text="セクター別資金フロー（直近30日）",
            font=dict(family="'Inter', sans-serif", size=14, color=ACCENT),
        ),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', monospace", color=TEXT_MUTED, size=11),
        margin=dict(l=120, r=80, t=50, b=30),
        height=max(400, len(df_sorted) * 32),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=True, zerolinecolor=TEXT_MUTED,
                   title="資金フロー指数"),
        yaxis=dict(showgrid=False),
    )
    return fig


# ─── メイン ───────────────────────────────────────────────────────────────

def main() -> None:
    st.title("🔄 セクター分析")
    st.caption(
        "TOPIX セクター ETF をもとに、セクターローテーション・資金フロー・"
        "月別リターンを可視化し、次に来るセクターを予測します。"
    )

    with st.sidebar:
        st.header("設定")
        if st.button("データ更新", use_container_width=True):
            fetch_sector_performance.clear()
            calc_fund_flow.clear()
            calc_monthly_sector_returns.clear()
            st.rerun()

    # ─── データ取得 ───────────────────────────────────────────────
    with st.spinner("セクターデータを取得中..."):
        perf_df = fetch_sector_performance()
        flow_df = calc_fund_flow()
        monthly_df = calc_monthly_sector_returns()

    if perf_df.empty:
        st.error("セクターデータの取得に失敗しました。しばらくしてからお試しください。")
        st.stop()

    rotation = detect_sector_rotation(perf_df)
    cycle_map = get_cycle_sector_map()

    # ─── タブ表示 ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "セクターパフォーマンス",
        "資金フロー",
        "月別リターン",
        "ローテーション予測",
    ])

    # ── Tab 1: パフォーマンス ──────────────────────────────────────
    with tab1:
        st.caption(
            "TOPIX業種別ETFの騰落率をセクターごとに比較。"
            "プラスは株価上昇、マイナスは下落を意味します。"
            "どの業種に資金が集まっているかを一目で把握できます。"
        )
        period_col = st.selectbox(
            "期間", ["1週間", "1ヶ月", "3ヶ月", "6ヶ月"],
            key="perf_period",
        )
        col_map = {"1週間": "return_1w", "1ヶ月": "return_1m", "3ヶ月": "return_3m", "6ヶ月": "return_6m"}
        col = col_map[period_col]

        if col in perf_df.columns:
            fig = _make_bar_chart(perf_df, col, f"セクター別リターン（{period_col}）")
            st.plotly_chart(fig, use_container_width=True)

        # サマリーメトリクス
        if not perf_df.empty and col in perf_df.columns:
            best = perf_df.loc[perf_df[col].idxmax()]
            worst = perf_df.loc[perf_df[col].idxmin()]
            c1, c2, c3 = st.columns(3)
            c1.metric("最強セクター", best["sector"], f"{best[col]:+.1f}%")
            c1.caption("選択期間内で最も上昇した業種")
            c2.metric("最弱セクター", worst["sector"], f"{worst[col]:+.1f}%")
            c2.caption("選択期間内で最も下落した業種")
            c3.metric("セクター間スプレッド", f"{best[col] - worst[col]:.1f}%pt")
            c3.caption("最強と最弱の差。大きいほど業種間格差が拡大")

    # ── Tab 2: 資金フロー ─────────────────────────────────────────
    with tab2:
        st.caption(
            "出来高×価格変動率の累積値で、セクターへの資金の流入・流出を推計。"
            "プラスは買いが優勢（資金流入）、マイナスは売りが優勢（資金流出）。"
            "機関投資家の動きを間接的に読み取れます。"
        )
        if not flow_df.empty:
            fig_flow = _make_fund_flow_chart(flow_df)
            st.plotly_chart(fig_flow, use_container_width=True)

            c1, c2 = st.columns(2)
            inflow = flow_df[flow_df["fund_flow"] > 0].sort_values("fund_flow", ascending=False)
            outflow = flow_df[flow_df["fund_flow"] < 0].sort_values("fund_flow", ascending=True)

            with c1:
                st.markdown("**資金流入セクター**")
                st.caption("直近30日で買い圧力が強い業種")
                for _, row in inflow.head(5).iterrows():
                    st.markdown(f"- {row['sector']}")

            with c2:
                st.markdown("**資金流出セクター**")
                st.caption("直近30日で売り圧力が強い業種")
                for _, row in outflow.head(5).iterrows():
                    st.markdown(f"- {row['sector']}")
        else:
            st.info("資金フローデータを取得できませんでした。")

    # ── Tab 3: 月別リターン ───────────────────────────────────────
    with tab3:
        st.caption(
            "各セクターの月ごとの騰落率をヒートマップで表示。"
            "緑が濃いほど上昇、赤が濃いほど下落。"
            "季節性やトレンドの変化を視覚的に確認できます。"
        )
        if not monthly_df.empty:
            fig_heat = _make_heatmap(monthly_df, "セクター別月次リターン")
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("月別リターンデータを取得できませんでした。")

    # ── Tab 4: ローテーション予測 ─────────────────────────────────
    with tab4:
        st.caption(
            "短期（1週間）と中期（1ヶ月）のリターン差から、資金の移動先を推定。"
            "景気サイクル（回復→拡大→後退→低迷）に基づき、"
            "次に有望なセクターを予測します。"
        )
        phase = rotation.get("cycle_phase", "不明")

        st.markdown(
            f"""<div style="
                background: rgba(10,15,26,0.5); border: 1px solid rgba(212,175,55,0.08);
                border-left: 2px solid #d4af37; border-radius: 2px; padding: 20px 28px;
            ">
                <span style="font-family:'Inter',sans-serif; font-size:0.65em; color:#d4af37;
                     letter-spacing:0.15em; text-transform:uppercase;">Current Cycle Phase</span>
                <div style="font-family:'Cormorant Garamond',serif; font-size:1.5em; color:#f0ece4;
                     margin-top:4px; letter-spacing:0.06em;">
                    {phase}
                </div>
                <div style="font-family:'Inter',sans-serif; font-size:0.65em; color:#6b7280; margin-top:6px;">
                    リーダーセクターの傾向から推定した現在の景気局面
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**リーダーセクター**（加速中）")
            st.caption("直近1週間のリターンがプラスかつ加速している業種。今まさに資金が向かっている先")
            for s in rotation.get("leaders", []):
                st.markdown(f"- {s}")

        with c2:
            st.markdown("**注目セクター**（浮上中）")
            st.caption("中期では低迷していたが、直近で回復の兆し。次のローテーション先の候補")
            for s in rotation.get("emerging", []):
                st.markdown(f"- {s}")

        with c3:
            st.markdown("**失速セクター**（減速中）")
            st.caption("直近で下落が加速している業種。資金が流出し始めている可能性")
            for s in rotation.get("laggards", []):
                st.markdown(f"- {s}")

        st.divider()

        # 景気サイクル別セクター
        st.subheader("景気サイクル × 有望セクター")
        st.caption(
            "景気の局面ごとに歴史的に強いセクター。"
            "現在の推定フェーズと照らし合わせることで、中長期の投資判断に活用できます。"
        )
        for cycle_phase, sectors in cycle_map.items():
            marker = " ← 現在" if cycle_phase == phase else ""
            st.markdown(f"**{cycle_phase}{marker}**")
            st.markdown("  " + "、".join(sectors))


main()

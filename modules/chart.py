import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_MA_COLORS = ["#2196F3", "#FF9800", "#4CAF50", "#E91E63", "#9C27B0"]


def _fmt(index: pd.Index) -> list[str]:
    """DatetimeIndex を 'YYYY-MM-DD' 文字列リストに変換する。"""
    return index.strftime("%Y-%m-%d").tolist()


def _snap_to_trading_day(date_str: str, trading_dates: list[str]) -> str | None:
    """
    イベント日付をチャート上の最近傍取引日にスナップする。
    取引日リストに存在しない場合（土日・祝日など）、
    前後 ±3 日で最も近い取引日を探す。
    見つからなければ None を返す。
    """
    if date_str in trading_dates:
        return date_str

    dt = pd.Timestamp(date_str)
    for delta in range(1, 4):
        for sign in [1, -1]:
            candidate = (dt + pd.Timedelta(days=delta * sign)).strftime("%Y-%m-%d")
            if candidate in trading_dates:
                return candidate
    return None


def create_candlestick_chart(
    df: pd.DataFrame,
    earnings_events: list[dict] | None = None,
    news_events: list[dict] | None = None,
    title: str = "",
    show_sma: list[int] | None = None,
    show_ema: list[int] | None = None,
    show_bb: bool = False,
    view_start_idx: int = 0,
    view_end_idx: int | None = None,
    chart_height: int = 630,
) -> tuple[go.Figure, int, int]:
    """
    ローソク足チャート（イベントマーカー付き）を生成する。

    x 軸を category 型にすることで非取引日（土日・祝日）の隙間を除去する。
    決算マーカー（★）とニュースマーカー（●）を常に最後の 2 トレースとして追加し、
    トレース番号を返すことでクリック検出に利用できる。

    Returns:
        (fig, earnings_trace_idx, news_trace_idx)
    """
    earnings_events = earnings_events or []
    news_events = news_events or []
    show_sma = show_sma or []
    show_ema = show_ema or []

    has_volume = "Volume" in df.columns
    trading_dates = _fmt(df.index)

    fig = make_subplots(
        rows=2 if has_volume else 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25] if has_volume else [1.0],
    )

    trace_idx = 0

    # ─── ローソク足（トレース 0） ───────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=trading_dates,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            name="ローソク足",
            showlegend=False,
        ),
        row=1, col=1,
    )
    trace_idx += 1

    # ─── SMA ────────────────────────────────────────────────────────
    for i, p in enumerate(sorted(show_sma)):
        col_name = f"SMA_{p}"
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=trading_dates, y=df[col_name],
                    line=dict(color=_MA_COLORS[i % len(_MA_COLORS)], width=1.2),
                    name=f"SMA {p}",
                ),
                row=1, col=1,
            )
            trace_idx += 1

    # ─── EMA ────────────────────────────────────────────────────────
    for i, p in enumerate(sorted(show_ema)):
        col_name = f"EMA_{p}"
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=trading_dates, y=df[col_name],
                    line=dict(color=_MA_COLORS[i % len(_MA_COLORS)], width=1.2, dash="dot"),
                    name=f"EMA {p}",
                ),
                row=1, col=1,
            )
            trace_idx += 1

    # ─── ボリンジャーバンド ──────────────────────────────────────────
    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["BB_upper"],
                line=dict(color="rgba(100,149,237,0.5)", width=1),
                name="BB上限",
            ),
            row=1, col=1,
        )
        trace_idx += 1
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["BB_lower"],
                line=dict(color="rgba(100,149,237,0.5)", width=1),
                fill="tonexty",
                fillcolor="rgba(100,149,237,0.07)",
                name="BB下限",
            ),
            row=1, col=1,
        )
        trace_idx += 1
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["BB_middle"],
                line=dict(color="rgba(100,149,237,0.8)", width=1, dash="dash"),
                name="BB中心",
                showlegend=False,
            ),
            row=1, col=1,
        )
        trace_idx += 1

    # ─── 出来高バー（row=2 だがグローバル番号はカウント） ─────────────
    if has_volume:
        colors = [
            "#26a69a" if c >= o else "#ef5350"
            for o, c in zip(df["Open"], df["Close"])
        ]
        fig.add_trace(
            go.Bar(
                x=trading_dates, y=df["Volume"],
                marker_color=colors,
                name="出来高",
                showlegend=False,
            ),
            row=2, col=1,
        )
        trace_idx += 1

        for vol_col in (c for c in df.columns if c.startswith("Vol_MA_")):
            fig.add_trace(
                go.Scatter(
                    x=trading_dates, y=df[vol_col],
                    line=dict(color="#FF9800", width=1),
                    name=f"出来高MA",
                ),
                row=2, col=1,
            )
            trace_idx += 1

    # ─── 決算マーカー（★）- 常に末尾から 2 番目 ─────────────────────
    earn_x, earn_y, earn_custom = [], [], []
    for ev in earnings_events:
        snapped = _snap_to_trading_day(ev["date"], trading_dates)
        if snapped:
            idx_pos = trading_dates.index(snapped)
            earn_x.append(snapped)
            earn_y.append(float(df["High"].iloc[idx_pos]) * 1.05)
            earn_custom.append(ev["date"])

    earnings_trace_idx = trace_idx
    fig.add_trace(
        go.Scatter(
            x=earn_x,
            y=earn_y,
            mode="markers+text",
            marker=dict(
                symbol="star",
                size=22,
                color="#FFD700",
                opacity=1.0,
                line=dict(color="#FF8C00", width=2),
            ),
            # 他の点が選択されても透明にならないよう opacity を固定
            unselected=dict(marker=dict(opacity=1.0, color="#FFD700")),
            selected=dict(marker=dict(opacity=1.0, size=26, color="#FFD700")),
            text=["決算"] * len(earn_x),
            textposition="top center",
            textfont=dict(size=11, color="#FFD700"),
            name="決算",
            customdata=earn_custom,
            hovertemplate="決算日: %{customdata}<br>クリックで詳細表示<extra></extra>",
        ),
        row=1, col=1,
    )
    trace_idx += 1

    # ─── ニュースマーカー（●）- 常に末尾 ──────────────────────────────
    news_x, news_y, news_custom, news_hover = [], [], [], []
    for ev in news_events:
        snapped = _snap_to_trading_day(ev["date"], trading_dates)
        if snapped:
            idx_pos = trading_dates.index(snapped)
            news_x.append(snapped)
            # 決算マーカーと重ならないよう少し上にオフセット
            news_y.append(float(df["High"].iloc[idx_pos]) * 1.048)
            news_custom.append(ev["date"])
            # ホバーに見出しの先頭を表示
            title_short = ev["title"][:40] + "…" if len(ev["title"]) > 40 else ev["title"]
            news_hover.append(title_short)

    news_trace_idx = trace_idx
    fig.add_trace(
        go.Scatter(
            x=news_x,
            y=news_y,
            mode="markers",
            marker=dict(
                symbol="circle",
                size=14,
                color="#00BCD4",
                opacity=1.0,
                line=dict(color="#0097A7", width=2),
            ),
            # 他の点が選択されても透明にならないよう opacity を固定
            unselected=dict(marker=dict(opacity=1.0, color="#00BCD4")),
            selected=dict(marker=dict(opacity=1.0, size=18, color="#00BCD4")),
            name="ニュース",
            customdata=list(zip(news_custom, news_hover)) if news_custom else [],
            hovertemplate="ニュース: %{customdata[1]}<br>日付: %{customdata[0]}<br>クリックで詳細表示<extra></extra>",
        ),
        row=1, col=1,
    )
    # trace_idx += 1  (最後のトレースなので不要)

    # ─── レイアウト ──────────────────────────────────────────────────
    end_idx = view_end_idx if view_end_idx is not None else len(df) - 1

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_rangeslider_visible=False,
        height=chart_height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        dragmode="pan",
        # clickmode="event+select" にすることで、dragmode="pan" のままでも
        # マーカーを単クリックすると Streamlit の on_select イベントが発火する
        clickmode="event+select",
    )
    # category 軸では range をインデックス値（±0.5 オフセット）で指定する。
    # 初期表示を選択期間に限定しつつ、パンで全期間を参照できる。
    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor="#2a2a2a",
        tickangle=-45,
        nticks=20,
        range=[view_start_idx - 0.5, end_idx + 0.5],
    )
    fig.update_yaxes(showgrid=True, gridcolor="#2a2a2a")

    return fig, earnings_trace_idx, news_trace_idx

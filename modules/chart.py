import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from modules.styles import BG_BASE, BG_PANEL, GRID_COLOR, TEXT_MUTED

_MA_COLORS = ["#3b9ddd", "#e6a817", "#4ade80", "#f472b6", "#a78bfa"]

# サブプロット行数に応じた高さ比率
_ROW_HEIGHTS = {
    # rows: (price, volume, extra...)
    1: [1.0],
    2: [0.78, 0.22],
    3: [0.60, 0.17, 0.23],
    4: [0.52, 0.14, 0.17, 0.17],
    5: [0.46, 0.12, 0.14, 0.14, 0.14],
}


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


def _osc_hline(fig, y: float, row: int, color: str, dash: str = "dash") -> None:
    """オシレーター基準線を追加するヘルパー。"""
    fig.add_hline(
        y=y,
        line_dash=dash,
        line_color=color,
        line_width=1,
        row=row,
        col=1,
    )


def create_candlestick_chart(
    df: pd.DataFrame,
    earnings_events: list[dict] | None = None,
    news_events: list[dict] | None = None,
    title: str = "",
    show_sma: list[int] | None = None,
    show_ema: list[int] | None = None,
    show_bb: bool = False,
    show_ichimoku: bool = False,
    show_rsi: bool = False,
    show_macd: bool = False,
    show_stoch: bool = False,
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

    # ─── サブプロット構成を動的に決定 ──────────────────────────────
    # extra_rows: RSI / MACD / Stochastic の有効なもの
    extra_panels: list[str] = []
    if show_rsi and "RSI_14" in df.columns:
        extra_panels.append("rsi")
    if show_stoch and "Stoch_K" in df.columns:
        extra_panels.append("stoch")
    if show_macd and "MACD" in df.columns:
        extra_panels.append("macd")

    total_rows = 1 + int(has_volume) + len(extra_panels)
    row_heights = _ROW_HEIGHTS.get(total_rows, _ROW_HEIGHTS[5])[:total_rows]
    # 合計が 1.0 になるよう正規化
    s = sum(row_heights)
    row_heights = [h / s for h in row_heights]

    # 各サブプロットが何行目に入るかを計算
    vol_row    = 2 if has_volume else None
    panel_rows = {}
    cur = 1 + int(has_volume)
    for name in extra_panels:
        cur += 1
        panel_rows[name] = cur

    specs = [[{"secondary_y": False}]] * total_rows
    subplot_titles = [""] * total_rows  # 空タイトル（後からアノテーション）

    fig = make_subplots(
        rows=total_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        specs=specs,
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

    # ─── 一目均衡表 ─────────────────────────────────────────────────
    if show_ichimoku and "Ichimoku_Tenkan" in df.columns:
        # 転換線（赤）
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Ichimoku_Tenkan"],
                line=dict(color="#ef5350", width=1), name="転換線",
            ),
            row=1, col=1,
        )
        trace_idx += 1
        # 基準線（青）
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Ichimoku_Kijun"],
                line=dict(color="#42a5f5", width=1), name="基準線",
            ),
            row=1, col=1,
        )
        trace_idx += 1
        # 先行スパンA（雲の上辺）
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Ichimoku_SpanA"],
                line=dict(color="rgba(76,175,80,0.4)", width=0.5),
                name="先行スパンA", showlegend=False,
            ),
            row=1, col=1,
        )
        trace_idx += 1
        # 先行スパンB（雲の下辺 + 雲の塗りつぶし）
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Ichimoku_SpanB"],
                line=dict(color="rgba(239,83,80,0.4)", width=0.5),
                fill="tonexty",
                fillcolor="rgba(76,175,80,0.06)",
                name="雲",
            ),
            row=1, col=1,
        )
        trace_idx += 1
        # 遅行線（緑）
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Ichimoku_Chikou"],
                line=dict(color="#66bb6a", width=1, dash="dot"),
                name="遅行線",
            ),
            row=1, col=1,
        )
        trace_idx += 1

    # ─── 出来高バー ─────────────────────────────────────────────────
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
                    name="出来高MA",
                ),
                row=2, col=1,
            )
            trace_idx += 1

    # ─── RSI サブプロット ────────────────────────────────────────────
    if "rsi" in panel_rows:
        r = panel_rows["rsi"]
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["RSI_14"],
                line=dict(color="#9C27B0", width=1.5),
                name="RSI(14)",
            ),
            row=r, col=1,
        )
        trace_idx += 1
        _osc_hline(fig, 70, r, "rgba(239,83,80,0.5)")
        _osc_hline(fig, 30, r, "rgba(38,166,154,0.5)")
        _osc_hline(fig, 50, r, "rgba(150,150,150,0.3)", dash="dot")
        fig.update_yaxes(range=[0, 100], row=r, col=1,
                         title_text="RSI", title_font_size=10)

    # ─── ストキャスティクス サブプロット ─────────────────────────────
    if "stoch" in panel_rows:
        r = panel_rows["stoch"]
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Stoch_K"],
                line=dict(color="#2196F3", width=1.5),
                name="%K(14)",
            ),
            row=r, col=1,
        )
        trace_idx += 1
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["Stoch_D"],
                line=dict(color="#FF9800", width=1.5),
                name="%D(3)",
            ),
            row=r, col=1,
        )
        trace_idx += 1
        _osc_hline(fig, 80, r, "rgba(239,83,80,0.5)")
        _osc_hline(fig, 20, r, "rgba(38,166,154,0.5)")
        fig.update_yaxes(range=[0, 100], row=r, col=1,
                         title_text="Stoch", title_font_size=10)

    # ─── MACD サブプロット ───────────────────────────────────────────
    if "macd" in panel_rows:
        r = panel_rows["macd"]
        hist_colors = [
            "#26a69a" if v >= 0 else "#ef5350"
            for v in df["MACD_Hist"].fillna(0)
        ]
        fig.add_trace(
            go.Bar(
                x=trading_dates, y=df["MACD_Hist"],
                marker_color=hist_colors,
                name="MACD Hist",
                showlegend=False,
            ),
            row=r, col=1,
        )
        trace_idx += 1
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["MACD"],
                line=dict(color="#2196F3", width=1.5),
                name="MACD",
            ),
            row=r, col=1,
        )
        trace_idx += 1
        fig.add_trace(
            go.Scatter(
                x=trading_dates, y=df["MACD_Signal"],
                line=dict(color="#FF9800", width=1.5),
                name="Signal",
            ),
            row=r, col=1,
        )
        trace_idx += 1
        _osc_hline(fig, 0, r, "rgba(150,150,150,0.4)", dash="dot")
        fig.update_yaxes(row=r, col=1, title_text="MACD", title_font_size=10)

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
                size=12,
                color="rgba(212, 175, 55, 0.6)",
                line=dict(color="#d4af37", width=1),
            ),
            unselected=dict(marker=dict(opacity=0.6, color="rgba(212, 175, 55, 0.6)")),
            selected=dict(marker=dict(opacity=1.0, size=18, color="#d4af37")),
            text=["決算"] * len(earn_x),
            textposition="top center",
            textfont=dict(size=9, color="rgba(212, 175, 55, 0.5)"),
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
            news_y.append(float(df["High"].iloc[idx_pos]) * 1.048)
            news_custom.append(ev["date"])
            title_short = ev["title"][:40] + "…" if len(ev["title"]) > 40 else ev["title"]
            news_hover.append(title_short)

    news_trace_idx = trace_idx
    fig.add_trace(
        go.Scatter(
            x=news_x,
            y=news_y,
            mode="markers",
            marker=dict(
                symbol="diamond",
                size=7,
                color="rgba(0, 188, 212, 0.45)",
                line=dict(color="#00BCD4", width=1),
            ),
            unselected=dict(marker=dict(opacity=0.45, color="rgba(0, 188, 212, 0.45)")),
            selected=dict(marker=dict(opacity=1.0, size=12, color="#00BCD4")),
            name="ニュース",
            customdata=list(zip(news_custom, news_hover)) if news_custom else [],
            hovertemplate="ニュース: %{customdata[1]}<br>日付: %{customdata[0]}<br>クリックで詳細表示<extra></extra>",
        ),
        row=1, col=1,
    )

    # ─── レイアウト ──────────────────────────────────────────────────
    end_idx = view_end_idx if view_end_idx is not None else len(df) - 1

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(
                family="'Inter', 'Noto Sans JP', sans-serif",
                size=14,
                color="#d4af37",
            ),
        ),
        xaxis_rangeslider_visible=False,
        height=chart_height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="'Inter', sans-serif", size=11, color=TEXT_MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=20, t=60, b=40),
        plot_bgcolor=BG_BASE,
        paper_bgcolor=BG_PANEL,
        font=dict(family="'IBM Plex Mono', 'Inter', monospace", color=TEXT_MUTED, size=11),
        dragmode="pan",
        clickmode="event+select",
    )

    # 全 x 軸に category 設定を適用
    # fixedrange=True で右スクロール防止、表示範囲はスライダーで制御
    fig.update_xaxes(
        type="category",
        showgrid=True,
        gridcolor=GRID_COLOR,
        tickangle=-45,
        nticks=min(20, end_idx - view_start_idx + 1),
        range=[view_start_idx - 0.5, end_idx + 0.5],
        fixedrange=True,
        autorange=False,
        tickfont=dict(family="'IBM Plex Mono', monospace", size=10),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        tickfont=dict(family="'IBM Plex Mono', monospace", size=10),
    )

    # ─── Y 軸を表示期間のデータにスコープ ────────────────────────────
    visible_df = df.iloc[view_start_idx : end_idx + 1]

    # 価格 (row=1)
    y_low  = float(visible_df["Low"].min())
    y_high = float(visible_df["High"].max())
    price_range = y_high - y_low
    fig.update_yaxes(
        range=[y_low - price_range * 0.05, y_high * 1.15],
        row=1, col=1,
    )

    # 出来高 (row=2): 95パーセンタイルを上限にして極端なスパイクを抑える
    if has_volume and "Volume" in visible_df.columns:
        vol_95 = float(visible_df["Volume"].quantile(0.95))
        if vol_95 > 0:
            fig.update_yaxes(range=[0, vol_95 * 2.0], row=2, col=1)

    # MACD: 表示期間の最大絶対値でシンメトリック範囲に
    if "macd" in panel_rows:
        r = panel_rows["macd"]
        macd_visible = pd.concat([
            visible_df[c].dropna()
            for c in ("MACD", "MACD_Signal", "MACD_Hist")
            if c in visible_df.columns
        ])
        if len(macd_visible) > 0:
            mabs = float(macd_visible.abs().max())
            if mabs > 0:
                fig.update_yaxes(range=[-mabs * 1.3, mabs * 1.3], row=r, col=1)

    return fig, earnings_trace_idx, news_trace_idx

"""
経済カレンダー

FOMC、日銀会合、雇用統計、CPI発表などのマクロイベントを表示。
AIが今週の注目イベントを解説。
"""

import json
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from modules.loading import helix_spinner
from modules.styles import apply_theme

apply_theme()

# ─── 主要イベント定義（2026年スケジュール）────────────────────────────────

# FOMC（米連邦公開市場委員会）2026年スケジュール
_FOMC_2026 = [
    ("2026-01-28", "2026-01-29", "FOMC会合（1月）"),
    ("2026-03-18", "2026-03-19", "FOMC会合（3月）※ドットプロット"),
    ("2026-05-06", "2026-05-07", "FOMC会合（5月）"),
    ("2026-06-17", "2026-06-18", "FOMC会合（6月）※ドットプロット"),
    ("2026-07-29", "2026-07-30", "FOMC会合（7月）"),
    ("2026-09-16", "2026-09-17", "FOMC会合（9月）※ドットプロット"),
    ("2026-11-04", "2026-11-05", "FOMC会合（11月）"),
    ("2026-12-16", "2026-12-17", "FOMC会合（12月）※ドットプロット"),
]

# 日銀金融政策決定会合 2026年スケジュール
_BOJ_2026 = [
    ("2026-01-23", "2026-01-24", "日銀会合（1月）"),
    ("2026-03-13", "2026-03-14", "日銀会合（3月）※展望レポート"),
    ("2026-04-30", "2026-05-01", "日銀会合（4-5月）※展望レポート"),
    ("2026-06-16", "2026-06-17", "日銀会合（6月）"),
    ("2026-07-16", "2026-07-17", "日銀会合（7月）※展望レポート"),
    ("2026-09-17", "2026-09-18", "日銀会合（9月）"),
    ("2026-10-29", "2026-10-30", "日銀会合（10月）※展望レポート"),
    ("2026-12-17", "2026-12-18", "日銀会合（12月）"),
]


def _build_key_events() -> list[dict]:
    """主要イベントの一覧を構築する。"""
    events = []
    today = date.today()
    year = today.year

    # FOMC
    for start, end, name in _FOMC_2026:
        events.append({
            "date": end,  # 結果発表は2日目
            "start": start,
            "name": name,
            "category": "FOMC",
            "country": "米国",
            "impact": "high",
            "icon": "🇺🇸",
        })

    # 日銀
    for start, end, name in _BOJ_2026:
        events.append({
            "date": end,
            "start": start,
            "name": name,
            "category": "日銀",
            "country": "日本",
            "impact": "high",
            "icon": "🇯🇵",
        })

    # 定期イベント（毎月）- 2026年の主要経済指標
    monthly_events = [
        (3, "米雇用統計（NFP）", "雇用", "米国", "high", "🇺🇸"),
        (10, "米CPI（消費者物価指数）", "CPI", "米国", "high", "🇺🇸"),
        (15, "米小売売上高", "小売", "米国", "medium", "🇺🇸"),
        (25, "米PCEデフレーター", "PCE", "米国", "high", "🇺🇸"),
        (1, "米ISM製造業景気指数", "ISM", "米国", "medium", "🇺🇸"),
        (20, "日本CPI", "CPI", "日本", "medium", "🇯🇵"),
    ]

    for month in range(1, 13):
        for day, name, cat, country, impact, icon in monthly_events:
            try:
                d = date(year, month, day)
                # 土日の場合は次の営業日に調整
                while d.weekday() >= 5:
                    d += timedelta(days=1)
                events.append({
                    "date": d.isoformat(),
                    "start": d.isoformat(),
                    "name": f"{name}（{month}月）",
                    "category": cat,
                    "country": country,
                    "impact": impact,
                    "icon": icon,
                })
            except ValueError:
                continue

    # 四半期GDP
    for month, label in [(1, "Q4"), (4, "Q1"), (7, "Q2"), (10, "Q3")]:
        try:
            d = date(year, month, 28)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            events.append({
                "date": d.isoformat(),
                "start": d.isoformat(),
                "name": f"米GDP速報値（{label}）",
                "category": "GDP",
                "country": "米国",
                "impact": "high",
                "icon": "🇺🇸",
            })
        except ValueError:
            continue

    events.sort(key=lambda x: x["date"])
    return events


# ─── Investing.com 経済カレンダー取得 ────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_investing_calendar() -> list[dict]:
    """Investing.com の経済カレンダーから直近のイベントを取得する。"""
    try:
        today = date.today()
        start = today - timedelta(days=1)
        end = today + timedelta(days=14)

        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []

        data = resp.json()
        events = []
        for item in data:
            title = item.get("title", "")
            country = item.get("country", "")
            event_date = item.get("date", "")[:10]
            impact = item.get("impact", "").lower()
            forecast = item.get("forecast", "")
            previous = item.get("previous", "")
            actual = item.get("actual", "")

            if not title or not event_date:
                continue

            # 国名を日本語化
            country_map = {
                "USD": ("米国", "🇺🇸"), "JPY": ("日本", "🇯🇵"),
                "EUR": ("欧州", "🇪🇺"), "GBP": ("英国", "🇬🇧"),
                "CNY": ("中国", "🇨🇳"), "AUD": ("豪州", "🇦🇺"),
            }
            country_ja, icon = country_map.get(country, (country, "🌐"))

            events.append({
                "date": event_date,
                "name": title,
                "country": country_ja,
                "icon": icon,
                "impact": "high" if impact == "high" else ("medium" if impact == "medium" else "low"),
                "forecast": str(forecast) if forecast else "",
                "previous": str(previous) if previous else "",
                "actual": str(actual) if actual else "",
                "category": "経済指標",
            })

        return events
    except Exception:
        return []


# ─── AI 今週の注目イベント解説 ───────────────────────────────────────────


@st.cache_data(ttl=3600 * 4, show_spinner=False)
def _get_weekly_commentary(events_text: str) -> str:
    """今週のイベントをAIが解説する。"""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        return ""

    prompt = f"""あなたは日本株投資家向けのマクロエコノミストです。
以下の今週の主要経済イベントについて、日本株への影響を中心に解説してください。

{events_text}

## ルール
- 提供されたイベント情報のみを使うこと
- 各イベントが日本株にどう影響するかを具体的に説明
- 最も注目すべきイベントを1つ選び、理由を説明
- 200〜300文字で簡潔に

日本語で回答してください。"""

    try:
        from modules.ai_analysis import _call_claude_with_fallback
        return _call_claude_with_fallback(prompt, api_key, model="claude-sonnet-4-6")
    except Exception:
        return ""


# ─── 描画 ────────────────────────────────────────────────────────────────

_IMPACT_STYLE = {
    "high": ("🔴", "#f47067", "重要"),
    "medium": ("🟡", "#e3b341", "中"),
    "low": ("⚪", "#6b7280", "低"),
}


def _render_event_card(event: dict, show_detail: bool = False, highlight: bool = False) -> None:
    """イベント1件をカードとして描画する。"""
    impact_icon, impact_color, impact_label = _IMPACT_STYLE.get(
        event.get("impact", "low"), ("⚪", "#6b7280", "低")
    )
    icon = event.get("icon", "🌐")
    forecast = event.get("forecast", "")
    previous = event.get("previous", "")
    actual = event.get("actual", "")

    detail_html = ""
    if show_detail and (forecast or previous or actual):
        parts = []
        if actual:
            parts.append(f"<b style='color:#f0ece4'>結果: {actual}</b>")
        if forecast:
            parts.append(f"予想: {forecast}")
        if previous:
            parts.append(f"前回: {previous}")
        detail_html = f"<br><span style='font-size:0.8em;color:#6b7280;margin-left:112px;'>{'　'.join(parts)}</span>"

    bg = "background:rgba(212,175,55,0.05);border-left:2px solid #d4af37;" if highlight else ""

    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
            border-bottom:1px solid rgba(26,31,46,0.5);flex-wrap:wrap;{bg}">
            <span style="font-size:0.8em;font-family:'IBM Plex Mono',monospace;
                   color:#6b7280;min-width:80px;">{event['date']}</span>
            <span style="min-width:22px;">{impact_icon}</span>
            <span style="min-width:28px;font-size:1.1em;">{icon}</span>
            <span style="font-family:'Inter','Noto Sans JP',sans-serif;font-size:0.88em;
                   color:#f0ece4;flex:1;">{event['name']}</span>
            <span style="font-size:0.7em;color:{impact_color};border:1px solid {impact_color}33;
                   padding:2px 8px;border-radius:2px;">{impact_label}</span>
            {detail_html}
        </div>""",
        unsafe_allow_html=True,
    )


# ─── メイン ──────────────────────────────────────────────────────────────


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>経済カレンダー</h1>",
        unsafe_allow_html=True,
    )
    st.caption("FOMC・日銀会合・雇用統計・CPIなど、株式市場に影響する主要マクロイベント")

    today = date.today()
    key_events = _build_key_events()

    # ── 外部カレンダーデータ取得 ──────────────────────────────
    with helix_spinner("経済カレンダーを取得中..."):
        external_events = _fetch_investing_calendar()

    # ── 今週のイベント ────────────────────────────────────────
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    this_week = [
        e for e in key_events
        if week_start.isoformat() <= e["date"] <= week_end.isoformat()
    ]
    this_week_ext = [
        e for e in external_events
        if week_start.isoformat() <= e["date"] <= week_end.isoformat()
        and e.get("impact") == "high"
    ]

    # 重複除去してマージ
    all_week = this_week.copy()
    seen_names = {e["name"][:15] for e in this_week}
    for e in this_week_ext:
        if e["name"][:15] not in seen_names:
            all_week.append(e)
            seen_names.add(e["name"][:15])
    all_week.sort(key=lambda x: x["date"])

    # ── AI 今週の注目イベント解説 ─────────────────────────────
    if all_week:
        events_text = "\n".join(
            f"- {e['date']} {e['icon']} {e['name']}（重要度: {_IMPACT_STYLE.get(e.get('impact', 'low'), ('', '', '低'))[2]}）"
            for e in all_week
        )
        with helix_spinner("AIが今週の注目イベントを分析中..."):
            commentary = _get_weekly_commentary(events_text)

        if commentary:
            st.markdown(
                f"""<div style="
                    background: rgba(10,15,26,0.5);
                    border: 1px solid rgba(212,175,55,0.06); border-left: 2px solid #d4af37;
                    border-radius: 2px; padding: 20px 28px; margin-bottom: 16px;
                ">
                    <div style="font-family:'Inter',sans-serif; font-size:0.6em; color:#d4af37;
                         text-transform:uppercase; letter-spacing:0.18em; margin-bottom:10px;">
                        Weekly Market Brief — AI Analysis
                    </div>
                    <div style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.88em;
                         color:#b8b0a2; line-height:1.8;">
                        {commentary}
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── タブ表示 ──────────────────────────────────────────────
    tab_week, tab_upcoming, tab_past, tab_all = st.tabs([
        "📅 今週", "🔜 今後2週間", "📋 直近の結果", "📆 年間スケジュール",
    ])

    with tab_week:
        if not all_week:
            st.info("今週は主要イベントがありません。")
        else:
            st.caption(f"今週のイベント（{week_start.strftime('%m/%d')}〜{week_end.strftime('%m/%d')}）")
            for e in all_week:
                is_today = e["date"] == today.isoformat()
                _render_event_card(e, show_detail=True, highlight=is_today)

    with tab_upcoming:
        upcoming_end = today + timedelta(days=14)
        upcoming = [e for e in key_events if today.isoformat() <= e["date"] <= upcoming_end.isoformat()]
        upcoming_ext = [
            e for e in external_events
            if today.isoformat() <= e["date"] <= upcoming_end.isoformat()
            and e.get("impact") in ("high", "medium")
        ]
        # マージ
        all_upcoming = upcoming.copy()
        seen = {e["name"][:15] for e in upcoming}
        for e in upcoming_ext:
            if e["name"][:15] not in seen:
                all_upcoming.append(e)
                seen.add(e["name"][:15])
        all_upcoming.sort(key=lambda x: x["date"])

        if not all_upcoming:
            st.info("今後2週間に主要イベントはありません。")
        else:
            st.caption(f"今後2週間のイベント（{today.strftime('%m/%d')}〜{upcoming_end.strftime('%m/%d')}）")
            for e in all_upcoming:
                _render_event_card(e, show_detail=True)

    with tab_past:
        past_start = today - timedelta(days=7)
        past_events = [
            e for e in external_events
            if past_start.isoformat() <= e["date"] < today.isoformat()
            and e.get("impact") in ("high", "medium")
            and e.get("actual")
        ]
        past_events.sort(key=lambda x: x["date"], reverse=True)

        if not past_events:
            st.info("直近1週間の結果データがありません。")
        else:
            st.caption("直近の経済指標結果")
            for e in past_events:
                _render_event_card(e, show_detail=True)

    with tab_all:
        # カテゴリフィルター
        cats = sorted({e.get("category", "") for e in key_events if e.get("category")})
        col1, col2 = st.columns([3, 1])
        with col2:
            selected_cat = st.selectbox("カテゴリ", ["全て"] + cats, key="econ_cal_cat")

        filtered = key_events
        if selected_cat != "全て":
            filtered = [e for e in key_events if e.get("category") == selected_cat]

        # 月ごとにグループ化
        from itertools import groupby
        for month_key, group in groupby(filtered, key=lambda x: x["date"][:7]):
            events_in_month = list(group)
            with st.expander(f"📅 {month_key}（{len(events_in_month)}件）", expanded=(month_key == today.strftime("%Y-%m"))):
                for e in events_in_month:
                    _past = e["date"] < today.isoformat()
                    if _past:
                        st.markdown(
                            f"<span style='color:#6b7280;font-size:0.85em;'>"
                            f"~~{e['date']}　{e['icon']} {e['name']}~~</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        _render_event_card(e)


main()

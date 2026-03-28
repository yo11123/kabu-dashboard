"""
市場ニュースまとめ

株式市場に影響しそうな世界・日本の最新ニュースをカテゴリ別に一覧表示。
Google News RSS から取得し、AIで要点を要約する。
"""

import pandas as pd
import streamlit as st

from modules.loading import helix_spinner
from modules.market_news import (
    NEWS_CATEGORIES,
    dedup_similar,
    fetch_all_news,
    fetch_category_news,
)
from modules.styles import apply_theme

apply_theme()

# カテゴリにアイコンを追加（表示用）
_CAT_ICONS = {
    "日本株・マーケット": "🇯🇵",
    "米国株・グローバル": "🇺🇸",
    "為替・金利": "💱",
    "地政学・国際情勢": "🌍",
    "コモディティ・エネルギー": "🛢️",
    "企業・決算": "🏢",
    "経済指標・マクロ": "📊",
    "テクノロジー・AI": "🤖",
}


# ─── AI 要約 ─────────────────────────────────────────────────────────────


def _build_summary_prompt(all_news: dict[str, list[dict]]) -> str:
    """全カテゴリのニュースから AI 要約用プロンプトを生成する。"""
    sections = []
    for cat_name, items in all_news.items():
        if not items:
            continue
        titles = "\n".join(f"- {it['title']}" for it in items[:10])
        sections.append(f"### {cat_name}\n{titles}")

    news_text = "\n\n".join(sections)

    return f"""あなたは金融市場のシニアアナリストです。
以下は本日の株式市場に関連するニュースの見出し一覧です。

{news_text}

## タスク
上記のニュース見出しを分析し、**株式市場への影響**の観点から要約してください。

## ★★★ 最重要ルール ★★★
- 上記の見出しに含まれる情報のみを使うこと
- あなたの訓練データや記憶にある情報は使用禁止
- 見出しにない事実を推測で補わないこと

## 出力形式（このJSONのみ出力。思考過程やコードブロック外のテキストは不要）
```json
{{
  "headline": "本日の市場を動かす最重要テーマ（1文、30文字以内）",
  "summary": "市場全体への影響を3〜4文で要約。具体的なニュース見出しを引用して根拠を示す",
  "bullish": ["強気材料1（見出しを引用）", "強気材料2", "強気材料3"],
  "bearish": ["弱気材料1（見出しを引用）", "弱気材料2", "弱気材料3"],
  "watchlist": ["今後注目すべきイベント/テーマ1", "注目2", "注目3"]
}}
```"""


@st.cache_data(ttl=1800, show_spinner=False)
def _get_news_summary(news_hash: str) -> dict:
    """ニュース要約をAIで生成する（30分キャッシュ）。"""
    import json
    import re

    all_news = fetch_all_news()
    prompt = _build_summary_prompt(all_news)

    try:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            api_key = ""
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY が未設定です"}

        from modules.ai_analysis import _call_claude
        text = _call_claude(prompt, api_key)

        if not text or not text.strip():
            return {"error": "AIから空の応答が返されました"}

        text = text.strip()
        # thinking タグ除去
        text = re.sub(r"<(?:ant)?[Tt]hinking>[\s\S]*?</(?:ant)?[Tt]hinking>", "", text).strip()

        # ```json ... ``` ブロック抽出
        code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
        for block in code_blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue

        # { ... } 抽出
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return json.loads(text)

    except Exception as e:
        return {"error": str(e)[:300]}


# ─── 描画 ────────────────────────────────────────────────────────────────


def _render_summary(summary: dict) -> None:
    """AI 要約を描画する。"""
    if summary.get("error"):
        st.warning(f"AI要約エラー: {summary['error']}")
        return

    headline = summary.get("headline", "")
    body = summary.get("summary", "")
    bulls = summary.get("bullish", [])
    bears = summary.get("bearish", [])
    watchlist = summary.get("watchlist", [])

    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.5);
            border: 1px solid rgba(212,175,55,0.06); border-left: 2px solid #d4af37;
            border-radius: 2px; padding: 24px 32px; margin-bottom: 16px;
        ">
            <div style="font-family:'Inter',sans-serif; font-size:0.6em; color:#d4af37;
                 text-transform:uppercase; letter-spacing:0.18em; margin-bottom:10px;">
                AI Market Brief — Claude Analysis
            </div>
            <div style="font-family:'Cormorant Garamond',serif; font-size:1.3em; font-weight:400;
                 color:#f0ece4; letter-spacing:0.05em; margin-bottom:12px;">
                {headline}
            </div>
            <div style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.88em;
                 color:#b8b0a2; line-height:1.8;">
                {body}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📈 強気材料**")
        for b in bulls:
            st.markdown(f"<span style='color:#5ca08b'>✅</span> {b}", unsafe_allow_html=True)
    with c2:
        st.markdown("**📉 弱気材料**")
        for b in bears:
            st.markdown(f"<span style='color:#c45c5c'>⚠️</span> {b}", unsafe_allow_html=True)
    with c3:
        st.markdown("**👀 注目テーマ**")
        for w in watchlist:
            st.markdown(f"<span style='color:#d4af37'>◆</span> {w}", unsafe_allow_html=True)


def _render_news_card(item: dict) -> None:
    """ニュース1件をカードとして描画する。"""
    pub_dt = item["pub_dt"]
    now = pd.Timestamp.now()
    delta = now - pub_dt

    # 経過時間表示
    if delta.total_seconds() < 3600:
        age = f"{int(delta.total_seconds() / 60)}分前"
    elif delta.total_seconds() < 86400:
        age = f"{int(delta.total_seconds() / 3600)}時間前"
    else:
        age = f"{int(delta.days)}日前"

    time_str = pub_dt.strftime("%m/%d %H:%M")
    publisher = item.get("publisher", "")
    link = item.get("link", "")

    pub_tag = f"<span style='color:#6b7280;font-size:0.8em'>{publisher}</span>" if publisher else ""
    link_tag = f"<a href='{link}' target='_blank' style='color:#8fb8a0;text-decoration:none;font-size:0.8em'>記事を読む →</a>" if link else ""

    st.markdown(
        f"""<div style="
            padding: 12px 16px; margin-bottom: 6px;
            border-bottom: 1px solid rgba(26,31,46,0.5);
        ">
            <div style="display:flex; align-items:baseline; gap:12px; flex-wrap:wrap;">
                <span style="color:#6b7280; font-size:0.75em; min-width:100px;
                       font-family:'IBM Plex Mono',monospace;">{time_str}  ({age})</span>
                <span style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.92em;
                       color:#f0ece4; flex:1;">{item['title']}</span>
                {pub_tag}
                {link_tag}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _format_time_ago(dt: pd.Timestamp) -> str:
    """更新時刻を「○分前」形式で返す。"""
    delta = pd.Timestamp.now() - dt
    if delta.total_seconds() < 60:
        return "たった今"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}分前"
    else:
        return f"{int(delta.total_seconds() / 3600)}時間前"


# ─── メイン ──────────────────────────────────────────────────────────────


def main() -> None:
    _title_col, _reload_col = st.columns([8, 2])
    with _title_col:
        st.markdown(
            "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
            " letter-spacing:0.12em; font-size:1.6rem;'>市場ニュースまとめ</h1>",
            unsafe_allow_html=True,
        )
    with _reload_col:
        _reload = st.button("🔄 最新ニュース取得", key="reload_news",
                            help="キャッシュをクリアして最新ニュースを取得します",
                            use_container_width=True)

    st.caption("株式市場に影響しそうな世界・日本の最新ニュースをカテゴリ別に表示。AIが要点を要約。")

    if _reload:
        fetch_category_news.clear()
        fetch_all_news.clear()
        _get_news_summary.clear()
        st.toast("キャッシュをクリアしました。最新ニュースを取得します。")

    # ─── ニュース取得 ─────────────────────────────────────────
    with helix_spinner("最新ニュースを取得中..."):
        all_news = fetch_all_news()

    total_count = sum(len(v) for v in all_news.values())
    if total_count == 0:
        st.warning("ニュースを取得できませんでした。しばらく待ってから再試行してください。")
        return

    # ─── AI 要約 ──────────────────────────────────────────────
    # ニュース内容のハッシュでキャッシュキーを生成
    _hash_input = "|".join(
        it["title"] for items in all_news.values() for it in items[:5]
    )
    _news_hash = str(hash(_hash_input))

    with helix_spinner("Claude がニュースを分析中..."):
        summary = _get_news_summary(_news_hash)
    _render_summary(summary)

    st.divider()

    # ─── カテゴリ別タブ表示 ────────────────────────────────────
    selected_cats = [c["name"] for c in NEWS_CATEGORIES]
    max_per_cat = 10

    tab_names = ["📋 全て"] + [
        f"{_CAT_ICONS.get(c['name'], '')} {c['name']}" for c in NEWS_CATEGORIES
    ]
    tabs = st.tabs(tab_names)

    # 全件タブ
    with tabs[0]:
        # 全カテゴリのニュースをマージして時系列順
        merged: list[dict] = []
        for cat in NEWS_CATEGORIES:
            if cat["name"] not in selected_cats:
                continue
            for item in all_news.get(cat["name"], []):
                item_copy = item.copy()
                item_copy["_category"] = cat["name"]
                item_copy["_icon"] = _CAT_ICONS.get(cat["name"], "")
                merged.append(item_copy)

        # 類似記事の除去（最も詳しい記事のみ残す）
        unique = dedup_similar(merged)
        unique.sort(key=lambda x: x["pub_dt"], reverse=True)

        st.caption(f"{len(unique)} 件のニュース")
        for item in unique[:50]:
            _render_news_card(item)

    # カテゴリ別タブ
    tab_idx = 1
    for cat in NEWS_CATEGORIES:
        if cat["name"] not in selected_cats:
            continue
        with tabs[tab_idx]:
            items = all_news.get(cat["name"], [])
            if not items:
                st.info(f"{cat['name']} のニュースが見つかりませんでした。")
            else:
                st.caption(f"{len(items)} 件")
                for item in items[:max_per_cat]:
                    _render_news_card(item)
        tab_idx += 1


if __name__ == "__main__":
    main()

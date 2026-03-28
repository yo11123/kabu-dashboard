"""
市場ニュースまとめ

株式市場に影響しそうな世界・日本の最新ニュースをカテゴリ別に一覧表示。
Google News RSS から取得し、AIで要点を要約する。
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

from modules.loading import helix_spinner
from modules.styles import apply_theme

apply_theme()

# ─── カテゴリ定義 ────────────────────────────────────────────────────────

NEWS_CATEGORIES: list[dict] = [
    {
        "name": "日本株・マーケット",
        "icon": "🇯🇵",
        "queries": [
            "日経平均 株価 マーケット",
            "東証 株式市場 相場",
        ],
    },
    {
        "name": "米国株・グローバル",
        "icon": "🇺🇸",
        "queries": [
            "米国株 S&P ナスダック ダウ",
            "米FRB 金利 利下げ 利上げ",
        ],
    },
    {
        "name": "為替・金利",
        "icon": "💱",
        "queries": [
            "ドル円 為替 円安 円高",
            "日本銀行 金融政策 金利",
        ],
    },
    {
        "name": "地政学・国際情勢",
        "icon": "🌍",
        "queries": [
            "地政学リスク 戦争 紛争 制裁",
            "米中 貿易摩擦 関税",
            "イラン イスラエル フーシ派 中東",
            "ウクライナ ロシア NATO 軍事",
            "北朝鮮 台湾 安全保障",
        ],
    },
    {
        "name": "コモディティ・エネルギー",
        "icon": "🛢️",
        "queries": [
            "原油 金 価格 商品",
            "エネルギー 資源 供給",
        ],
    },
    {
        "name": "企業・決算",
        "icon": "🏢",
        "queries": [
            "企業決算 業績 上方修正 下方修正",
            "M&A 買収 上場 IPO",
        ],
    },
    {
        "name": "経済指標・マクロ",
        "icon": "📊",
        "queries": [
            "GDP CPI 雇用統計 経済指標",
            "景気 インフレ デフレ 経済",
        ],
    },
    {
        "name": "テクノロジー・AI",
        "icon": "🤖",
        "queries": [
            "AI 半導体 テクノロジー 株",
            "NVIDIA OpenAI テック 投資",
        ],
    },
]


# ─── ニュース取得 ────────────────────────────────────────────────────────


def _fetch_rss(query: str, max_items: int = 15) -> list[dict]:
    """Google News RSS から記事を取得する（1週間以内のみ）。"""
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    try:
        # when:7d で直近7日間に限定
        url = (
            "https://news.google.com/rss/search"
            f"?q={urllib.parse.quote(query)}+when:7d&hl=ja&gl=JP&ceid=JP:ja"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; kabu-dashboard/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items: list[dict] = []

        for item_el in root.findall(".//item"):
            title = item_el.findtext("title", "").strip()
            link = item_el.findtext("link", "").strip()
            pub_date_str = item_el.findtext("pubDate", "")
            source_el = item_el.find("source")
            publisher = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else ""
            )

            if not title or not pub_date_str:
                continue

            # 末尾 " - 出版社名" を除去
            if publisher:
                suffix = f" - {publisher}"
                if title.endswith(suffix):
                    title = title[: -len(suffix)].strip()

            try:
                pub_dt = pd.Timestamp(pub_date_str)
                if pub_dt.tz is not None:
                    pub_dt = pub_dt.tz_convert("Asia/Tokyo").tz_localize(None)
            except Exception:
                continue

            # 1週間以内のみ
            if pub_dt < cutoff:
                continue

            items.append({
                "pub_dt": pub_dt,
                "title": title,
                "publisher": publisher,
                "link": link,
            })

        # 最新順ソート
        items.sort(key=lambda x: x["pub_dt"], reverse=True)
        return items[:max_items]
    except Exception:
        return []


def _tokenize(title: str) -> set[str]:
    """タイトルを簡易トークン化する（助詞・記号を除去し、キーワード集合を返す）。"""
    import re
    # 記号・空白で分割し、1文字以下のトークンを除去
    tokens = re.split(r'[\s,、。・/\-\|「」『』（）()【】\[\]：:]+', title)
    # 短すぎるトークン（助詞等）を除外
    stop = {"の", "は", "が", "を", "に", "で", "と", "も", "へ", "や", "か", "な",
            "だ", "た", "て", "する", "した", "から", "まで", "より", "など",
            "ら", "れ", "さ", "し", "い", "る", "ない", "ある", "いる",
            "the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "on"}
    return {t.lower() for t in tokens if len(t) > 1 and t.lower() not in stop}


def _similarity(a: set[str], b: set[str]) -> float:
    """2つのトークン集合のJaccard類似度を返す。"""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _dedup_similar(items: list[dict], threshold: float = 0.45) -> list[dict]:
    """類似ニュースをグループ化し、各グループから最も詳しい記事のみ残す。

    「詳しい」= タイトルが長い記事を優先（より多くの情報を含む）。
    同じ長さなら出版社の優先度で判定。
    """
    _PUBLISHER_PRIORITY = {
        "日本経済新聞": 0, "日経": 0, "ロイター": 1, "Reuters": 1,
        "Bloomberg": 2, "ブルームバーグ": 2, "株探": 3, "東洋経済": 4,
        "NHK": 2, "朝日新聞": 3, "読売新聞": 3, "毎日新聞": 3,
    }

    def _priority(item: dict) -> int:
        pub = item.get("publisher", "")
        for name, pri in _PUBLISHER_PRIORITY.items():
            if name in pub:
                return pri
        return 9

    if not items:
        return []

    # トークン化
    tokenized = [(item, _tokenize(item["title"])) for item in items]

    # グループ化: 各記事を既存グループと比較し、類似ならマージ
    groups: list[list[int]] = []  # index のリスト
    assigned: set[int] = set()

    for i, (_, tokens_i) in enumerate(tokenized):
        if i in assigned:
            continue

        group = [i]
        assigned.add(i)

        for j, (_, tokens_j) in enumerate(tokenized):
            if j in assigned:
                continue
            if _similarity(tokens_i, tokens_j) >= threshold:
                group.append(j)
                assigned.add(j)

        groups.append(group)

    # 各グループから最も詳しい記事を選択
    result: list[dict] = []
    for group in groups:
        candidates = [items[idx] for idx in group]
        # タイトル長い順 → 出版社優先度順
        candidates.sort(key=lambda x: (-len(x["title"]), _priority(x)))
        result.append(candidates[0])

    return result


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_category_news(queries: tuple[str, ...], max_items: int = 20) -> list[dict]:
    """カテゴリ内の全クエリからニュースを取得しマージ・類似記事を除去する。"""
    all_items: list[dict] = []
    for q in queries:
        all_items.extend(_fetch_rss(q, max_items=15))

    # 完全重複除去（タイトル先頭35文字）
    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_items:
        key = item["title"][:35]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 類似記事の除去（最も詳しい記事のみ残す）
    deduped = _dedup_similar(unique)
    deduped.sort(key=lambda x: x["pub_dt"], reverse=True)
    return deduped[:max_items]


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_all_news() -> dict[str, list[dict]]:
    """全カテゴリのニュースを一括取得する。"""
    result: dict[str, list[dict]] = {}
    for cat in NEWS_CATEGORIES:
        items = _fetch_category_news(tuple(cat["queries"]), max_items=20)
        result[cat["name"]] = items
    return result


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

    all_news = _fetch_all_news()
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
        _fetch_category_news.clear()
        _fetch_all_news.clear()
        _get_news_summary.clear()
        st.toast("キャッシュをクリアしました。最新ニュースを取得します。")

    # ─── ニュース取得 ─────────────────────────────────────────
    with helix_spinner("最新ニュースを取得中..."):
        all_news = _fetch_all_news()

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
        f"{c['icon']} {c['name']}" for c in NEWS_CATEGORIES
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
                item_copy["_icon"] = cat["icon"]
                merged.append(item_copy)

        # 類似記事の除去（最も詳しい記事のみ残す）
        unique = _dedup_similar(merged)
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

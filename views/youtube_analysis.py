"""
YouTube動画分析ページ
株式関連のYouTube動画を字幕から分析し、投資インサイトを抽出する。
"""
import html
import streamlit as st

from modules.styles import apply_theme
from modules.youtube_analyzer import (
    analyze_videos,
    chat_with_videos,
    extract_video_id,
    generate_integrated_report,
    load_reports,
    load_youtube_summaries,
    save_report,
    save_youtube_summaries,
)

apply_theme()


def _get_gemini_key() -> str:
    """Gemini API キーを取得する。"""
    key = ""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    if not key:
        key = st.sidebar.text_input(
            "Gemini API Key",
            type="password",
            help="https://aistudio.google.com/apikey から無料で取得できます",
        )
    return key


def _show_key_guide() -> None:
    st.info(
        "Gemini API キーが必要です。\n\n"
        "1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス\n"
        "2. 「APIキーを作成」をクリック\n"
        "3. サイドバーにキーを入力、または `secrets.toml` に `GEMINI_API_KEY = \"...\"` を追加\n\n"
        "**完全無料**で1日1,500リクエストまで利用できます。"
    )


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>YouTube 動画分析</h1>",
        unsafe_allow_html=True,
    )
    st.caption("株式関連のYouTube動画を字幕から自動分析し、投資インサイトを抽出します（Gemini API 無料枠使用）")

    gemini_key = _get_gemini_key()
    if not gemini_key:
        _show_key_guide()

    # ── タブ構成 ──────────────────────────────────────────
    history = load_youtube_summaries()
    history_count = len(history)

    tab_analyze, tab_report, tab_qa = st.tabs([
        "動画分析",
        f"統合レポート ({history_count}本)",
        "動画Q&A",
    ])

    with tab_analyze:
        _render_analyze_tab(gemini_key, history)

    with tab_report:
        _render_report_tab(gemini_key, history)

    with tab_qa:
        _render_qa_tab(gemini_key, history)


# ═══════════════════════════════════════════════════════════════════
# タブ1: 動画分析
# ═══════════════════════════════════════════════════════════════════


def _render_analyze_tab(gemini_key: str, history: list[dict]) -> None:
    st.markdown("### 動画URLを入力")

    urls_text = st.text_area(
        "YouTube URL（1行に1つ）",
        height=120,
        placeholder="https://www.youtube.com/watch?v=xxxxx\nhttps://youtu.be/yyyyy",
    )

    analyze_btn = st.button("分析開始", type="primary", disabled=not gemini_key)

    if analyze_btn and urls_text.strip():
        urls = [u.strip() for u in urls_text.strip().split("\n") if u.strip()]
        if not urls:
            st.warning("URLを入力してください")
        elif len(urls) > 10:
            st.warning("一度に分析できるのは10動画までです")
        else:
            valid_urls = []
            for url in urls:
                vid = extract_video_id(url)
                if vid:
                    valid_urls.append(url)
                else:
                    st.warning(f"無効なURL: {url}")

            if valid_urls:
                progress = st.progress(0)
                with st.spinner(f"{len(valid_urls)}本の動画を分析中..."):
                    results = analyze_videos(valid_urls, gemini_key, progress)
                save_youtube_summaries(results)
                st.success(f"{len(results)}本の動画を分析しました")
                _display_results(results)

    # 履歴
    st.divider()
    st.markdown("### 分析履歴")
    if not history:
        st.caption("まだ分析結果がありません。上のフォームからYouTube URLを入力して分析を開始してください。")
    else:
        st.caption(f"{len(history)}件の分析結果")
        _display_results(history)


# ═══════════════════════════════════════════════════════════════════
# タブ2: 統合レポート
# ═══════════════════════════════════════════════════════════════════


def _render_report_tab(gemini_key: str, history: list[dict]) -> None:
    if not history:
        st.info("まず「動画分析」タブで動画を分析してください。分析結果を統合してレポートを生成します。")
        return

    st.markdown("### 統合レポート生成")
    st.caption("分析済みの複数動画を統合し、包括的なマーケットレポートを自動生成します")

    # 動画選択
    valid_history = [
        h for h in history
        if isinstance(h.get("summary"), dict) and "error" not in h.get("summary", {})
    ]

    if not valid_history:
        st.warning("有効な分析結果がありません。")
        return

    # チェックボックスで選択
    st.markdown("**レポートに含める動画を選択:**")

    selected_ids = []
    for i, h in enumerate(valid_history[:20]):
        title = h.get("title", "不明な動画")
        analysis_date = h.get("date", "")
        checked = st.checkbox(
            f"{title}  ({analysis_date})",
            value=i < 5,  # 最新5本はデフォルト選択
            key=f"report_sel_{h.get('video_id', i)}",
        )
        if checked:
            selected_ids.append(i)

    selected = [valid_history[i] for i in selected_ids]
    st.caption(f"{len(selected)}本の動画を選択中")

    # レポート生成
    if st.button("レポート生成", type="primary", disabled=not gemini_key or not selected):
        with st.spinner(f"{len(selected)}本の動画を統合分析中..."):
            report = generate_integrated_report(selected, gemini_key)

        # 永続保存
        video_titles = [s.get("title", "不明") for s in selected]
        save_report(report, video_titles)

        st.divider()
        st.markdown(report)

        st.download_button(
            "レポートをダウンロード (.md)",
            data=report,
            file_name="market_report.md",
            mime="text/markdown",
        )

    # 過去のレポート履歴
    saved_reports = load_reports()
    if saved_reports:
        st.divider()
        st.markdown("### 過去のレポート")
        for i, rpt in enumerate(saved_reports):
            rpt_date = rpt.get("date", "不明")
            rpt_count = rpt.get("video_count", 0)
            rpt_titles = rpt.get("video_titles", [])
            label = f"{rpt_date} ({rpt_count}本の動画から生成)"
            with st.expander(label, expanded=i == 0):
                st.markdown(rpt.get("report", ""))
                if rpt_titles:
                    st.caption("参照動画: " + " / ".join(rpt_titles[:5]))
                col_dl, col_del, _ = st.columns([1, 1, 4])
                col_dl.download_button(
                    "ダウンロード",
                    data=rpt.get("report", ""),
                    file_name=f"market_report_{rpt_date}.md",
                    mime="text/markdown",
                    key=f"dl_rpt_{i}",
                )
                if col_del.button("削除", key=f"del_rpt_{i}"):
                    saved_reports.pop(i)
                    from modules.persistence import _file_save, _sync_to_gist
                    _file_save("youtube_reports", saved_reports)
                    _sync_to_gist()
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════
# タブ3: 動画Q&A
# ═══════════════════════════════════════════════════════════════════


def _render_qa_tab(gemini_key: str, history: list[dict]) -> None:
    if not history:
        st.info("まず「動画分析」タブで動画を分析してください。分析済みの動画について質問できます。")
        return

    st.markdown("### 動画Q&A")
    st.caption("分析済みの動画の内容について質問できます")

    # 動画選択
    valid_history = [
        h for h in history
        if isinstance(h.get("summary"), dict) and "error" not in h.get("summary", {})
    ]

    if not valid_history:
        st.warning("有効な分析結果がありません。")
        return

    titles = [f"{h.get('title', '不明')} ({h.get('date', '')})" for h in valid_history[:20]]
    selected_indices = st.multiselect(
        "質問対象の動画を選択",
        range(len(titles)),
        default=list(range(min(3, len(titles)))),
        format_func=lambda i: titles[i],
    )
    selected = [valid_history[i] for i in selected_indices]

    if not selected:
        st.caption("動画を選択してください")
        return

    st.caption(f"{len(selected)}本の動画を参照")

    # チャット履歴の初期化
    if "yt_chat_history" not in st.session_state:
        st.session_state["yt_chat_history"] = []

    # チャット履歴表示
    for msg in st.session_state["yt_chat_history"]:
        role = msg["role"]
        _escaped = html.escape(msg["content"]).replace("\n", "<br>")
        if role == "user":
            st.markdown(
                f"<div style='background:#1a2233; border-radius:8px; padding:10px 14px;"
                f" margin:6px 0 6px 40px; border:1px solid #2a3a50;'>"
                f"<span style='color:#9ca3af; font-size:0.75em;'>あなた</span><br>"
                f"{_escaped}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#0f1a2a; border-radius:8px; padding:10px 14px;"
                f" margin:6px 40px 6px 0; border:1px solid #1a2a3a;'>"
                f"<span style='color:#5ca08b; font-size:0.75em;'>AI</span><br>"
                f"{_escaped}</div>",
                unsafe_allow_html=True,
            )

    # 質問入力
    question = st.chat_input("動画の内容について質問...", disabled=not gemini_key)

    if question:
        if len(question) > 2000:
            st.warning("入力は2000文字以内にしてください。")
        else:
            # ユーザーメッセージを追加
            st.session_state["yt_chat_history"].append({"role": "user", "content": question})

            # 回答生成
            with st.spinner("回答を生成中..."):
                answer = chat_with_videos(
                    question,
                    selected,
                    gemini_key,
                    st.session_state["yt_chat_history"],
                )

            st.session_state["yt_chat_history"].append({"role": "assistant", "content": answer})
            st.rerun()

    # クリアボタン
    col1, col2 = st.columns([1, 5])
    if col1.button("会話をクリア"):
        st.session_state["yt_chat_history"] = []
        st.rerun()

    # 質問例
    if not st.session_state["yt_chat_history"]:
        st.markdown("**質問例:**")
        examples = [
            "この動画で推奨されている銘柄は？",
            "市場のリスク要因をまとめて",
            "半導体セクターについてどう言っている？",
            "今週注目すべきイベントは？",
            "買い時と判断している銘柄の根拠は？",
        ]
        cols = st.columns(len(examples))
        for i, ex in enumerate(examples):
            if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["yt_chat_history"].append({"role": "user", "content": ex})
                with st.spinner("回答を生成中..."):
                    answer = chat_with_videos(ex, selected, gemini_key, [])
                st.session_state["yt_chat_history"].append({"role": "assistant", "content": answer})
                st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 分析結果表示
# ═══════════════════════════════════════════════════════════════════


def _display_results(results: list[dict]) -> None:
    """分析結果を表示する。"""
    for r in results:
        if "error" in r and "summary" not in r:
            st.error(f"{r.get('title', r.get('url', '不明'))}: {r['error']}")
            continue

        summary = r.get("summary", {})
        if isinstance(summary, dict) and "error" in summary:
            st.warning(f"{r.get('title', r.get('url', ''))}: {summary['error']}")
            continue

        title = r.get("title", "不明な動画")
        video_id = r.get("video_id", "")
        analysis_date = r.get("date", "")

        with st.expander(f"{title}  ({analysis_date})", expanded=len(results) <= 3):
            if video_id:
                st.caption(f"https://www.youtube.com/watch?v={video_id}")

            if not isinstance(summary, dict):
                st.write(str(summary))
                continue

            if summary.get("title_summary"):
                st.markdown(f"**{summary['title_summary']}**")

            if summary.get("market_outlook"):
                outlook = summary["market_outlook"]
                color = "#5ca08b" if "強気" in outlook else ("#c45c5c" if "弱気" in outlook else "#6b7280")
                st.markdown(
                    f"<div style='border-left:3px solid {color}; padding:8px 16px; "
                    f"background:rgba(10,15,26,0.3); margin:8px 0; border-radius:2px;'>"
                    f"<span style='color:{color}; font-weight:600;'>市場見通し:</span> {outlook}</div>",
                    unsafe_allow_html=True,
                )

            tickers = summary.get("mentioned_tickers", [])
            if tickers:
                st.markdown("**言及銘柄:**")
                cols = st.columns(min(len(tickers), 4))
                for i, t in enumerate(tickers[:8]):
                    col = cols[i % len(cols)]
                    direction = t.get("direction", "中立")
                    d_color = "#5ca08b" if "買" in direction else ("#c45c5c" if "売" in direction else "#6b7280")
                    col.markdown(
                        f"<div style='border:1px solid {d_color}33; border-radius:4px; "
                        f"padding:6px 10px; margin:2px 0; font-size:0.85em;'>"
                        f"<span style='color:{d_color}; font-weight:600;'>{t.get('ticker', '?')}</span> "
                        f"<span style='color:{d_color};'>{direction}</span><br>"
                        f"<span style='color:#9ca3af; font-size:0.85em;'>{t.get('reason', '')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            key_points = summary.get("key_points", [])
            if key_points:
                st.markdown("**要点:**")
                for kp in key_points:
                    st.markdown(f"- {kp}")

            c1, c2 = st.columns(2)
            catalysts = summary.get("catalysts", [])
            risks = summary.get("risk_factors", [])

            if catalysts:
                with c1:
                    st.markdown("**カタリスト:**")
                    for c in catalysts:
                        st.markdown(f"- {c}")
            if risks:
                with c2:
                    st.markdown("**リスク:**")
                    for risk in risks:
                        st.markdown(f"- {risk}")

            sector = summary.get("sector_outlook", {})
            if sector and isinstance(sector, dict):
                st.markdown("**セクター見通し:**")
                sector_text = " / ".join(f"{k}: {v}" for k, v in sector.items())
                st.caption(sector_text)

            confidence = summary.get("confidence", "")
            source_method = r.get("source_method", "")
            captions = []
            if confidence:
                captions.append(f"信頼度: {confidence}")
            if source_method:
                captions.append(f"分析方法: {source_method}")
            if summary.get("_source") == "NotebookLM":
                captions.append("via NotebookLM")
            if captions:
                st.caption(" | ".join(captions))

            if st.button("削除", key=f"del_{video_id}_{analysis_date}"):
                all_history = load_youtube_summaries()
                all_history = [h for h in all_history if h.get("video_id") != video_id]
                from modules.persistence import _file_save, _sync_to_gist
                _file_save("youtube_summaries", all_history)
                _sync_to_gist()
                st.rerun()


main()

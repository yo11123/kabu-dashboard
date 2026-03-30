"""
作者の相場観 — 編集・表示ページ

テキストエリアで相場観を書くだけで、買い時銘柄ページに自動表示される。
データはGist/ローカルに永続化。
"""
import streamlit as st

from modules.persistence import _file_save, _file_load, _sync_to_gist
from modules.styles import apply_theme

apply_theme()

_KEY = "author_note"


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>制作者相場観</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-family:Inter,Noto Sans JP,sans-serif;font-size:0.85em;"
        "color:#6b7280;line-height:1.8;margin-bottom:16px;'>"
        "このページはアプリ制作者が、AI分析とは別に個人的に感じている日本株市場の相場観を"
        "書き留めるスペースです。やる気があれば随時更新していきます。"
        "<br>あくまで個人の見解であり、投資助言ではありません。"
        "</div>",
        unsafe_allow_html=True,
    )

    # 保存済みの内容を読み込み
    saved = _file_load(_KEY, "")
    if not isinstance(saved, str):
        saved = ""

    # ── 閲覧（誰でも見れる）──────────────────────────────────
    if saved.strip():
        st.markdown(
            f"""<div style="
                background: rgba(10,15,26,0.5);
                border: 1px solid rgba(143,184,160,0.1); border-left: 2px solid #8fb8a0;
                border-radius: 2px; padding: 16px 24px; margin-bottom: 16px;
            ">
                <div style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.88em;
                     color:#b8b0a2; line-height:1.8; white-space:pre-wrap;">
                    {saved.strip()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("まだ相場観が投稿されていません。")

    st.divider()

    # ── 編集（パスワード保護）─────────────────────────────────
    try:
        _correct_pw = st.secrets.get("AUTHOR_PASSWORD", "")
    except Exception:
        _correct_pw = ""

    if not _correct_pw:
        st.caption("編集機能を使うには Streamlit Cloud の Secrets に `AUTHOR_PASSWORD` を設定してください。")
        return

    with st.expander("✏️ 編集（制作者のみ）"):
        pw = st.text_input("パスワード", type="password", key="author_pw")
        if pw and pw == _correct_pw:
            note = st.text_area(
                "相場観を入力",
                value=saved,
                height=300,
                placeholder="例: 中東情勢の緊迫化で原油が急騰。ただし円安で輸出企業には追い風。",
                key="author_note_input",
            )
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💾 保存", type="primary", use_container_width=True):
                    _file_save(_KEY, note)
                    _sync_to_gist()
                    st.success("保存しました")
                    st.rerun()
            with col2:
                if st.button("🗑️ クリア", use_container_width=True):
                    _file_save(_KEY, "")
                    _sync_to_gist()
                    st.rerun()
        elif pw:
            st.error("パスワードが違います")

    note = saved  # プレビュー用

    # プレビュー
    if note.strip():
        st.divider()
        st.caption("プレビュー（買い時銘柄ページでの表示イメージ）")
        st.markdown(
            f"""<div style="
                background: rgba(10,15,26,0.5);
                border: 1px solid rgba(143,184,160,0.1); border-left: 2px solid #8fb8a0;
                border-radius: 2px; padding: 16px 24px;
            ">
                <div style="font-family:'Inter',sans-serif; font-size:0.6em; color:#8fb8a0;
                     text-transform:uppercase; letter-spacing:0.18em; margin-bottom:8px;">
                    Author's Market View
                </div>
                <div style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.88em;
                     color:#b8b0a2; line-height:1.8; white-space:pre-wrap;">
                    {note.strip()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )


main()

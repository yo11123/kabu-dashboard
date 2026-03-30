"""
制作者相場観 — 編集・表示ページ

テキストエリアで相場観を書くだけで、買い時銘柄ページに自動表示される。
過去の投稿も履歴として閲覧可能。データはGist/ローカルに永続化。
"""
from datetime import date

import streamlit as st

from modules.persistence import _file_save, _file_load, _sync_to_gist
from modules.styles import apply_theme

apply_theme()

_KEY = "author_note"
_HISTORY_KEY = "author_note_history"


def _load_history() -> list[dict]:
    """投稿履歴を読み込む（日付降順）。"""
    h = _file_load(_HISTORY_KEY, [])
    if not isinstance(h, list):
        return []
    return h


def _save_to_history(content: str) -> None:
    """現在の内容を履歴に追加して保存する。"""
    history = _load_history()
    today = date.today().isoformat()

    # 同日の投稿があれば上書き
    history = [e for e in history if e.get("date") != today]
    history.insert(0, {"date": today, "content": content})

    # 最大60件保持
    history = history[:60]

    _file_save(_HISTORY_KEY, history)
    _file_save(_KEY, content)
    _sync_to_gist()


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

    saved = _file_load(_KEY, "")
    if not isinstance(saved, str):
        saved = ""
    history = _load_history()

    # ── 最新の相場観（誰でも見れる）──────────────────────────────
    if saved.strip():
        _post_date = history[0]["date"] if history else "—"
        st.markdown(
            f"""<div style="
                background: rgba(10,15,26,0.5);
                border: 1px solid rgba(143,184,160,0.1); border-left: 2px solid #8fb8a0;
                border-radius: 2px; padding: 16px 24px; margin-bottom: 16px;
            ">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-family:'Inter',sans-serif; font-size:0.6em; color:#8fb8a0;
                         text-transform:uppercase; letter-spacing:0.18em;">
                        Latest — Author's Market View
                    </span>
                    <span style="font-family:'IBM Plex Mono',monospace; font-size:0.75em; color:#6b7280;">
                        {_post_date}
                    </span>
                </div>
                <div style="font-family:'Inter','Noto Sans JP',sans-serif; font-size:0.88em;
                     color:#b8b0a2; line-height:1.8; white-space:pre-wrap;">
                    {saved.strip()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("まだ相場観が投稿されていません。")

    # ── 編集（パスワード保護）─────────────────────────────────
    try:
        _correct_pw = st.secrets.get("AUTHOR_PASSWORD", "")
    except Exception:
        _correct_pw = ""

    if _correct_pw:
        with st.expander("✏️ 編集（制作者のみ）"):
            pw = st.text_input("パスワード", type="password", key="author_pw")
            if pw and pw == _correct_pw:
                note = st.text_area(
                    "相場観を入力",
                    value=saved,
                    height=250,
                    placeholder="例: 中東情勢の緊迫化で原油が急騰。ただし円安で輸出企業には追い風。",
                    key="author_note_input",
                )
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("💾 保存", type="primary", use_container_width=True):
                        _save_to_history(note)
                        st.success("保存しました")
                        st.rerun()
                with col2:
                    if st.button("🗑️ クリア", use_container_width=True):
                        _file_save(_KEY, "")
                        _sync_to_gist()
                        st.rerun()
            elif pw:
                st.error("パスワードが違います")

    # ── 過去の投稿履歴 ───────────────────────────────────────
    if history:
        st.divider()
        st.markdown("**過去の投稿**")

        for entry in history:
            _d = entry.get("date", "")
            _c = entry.get("content", "").strip()
            if not _c:
                continue
            # 最新投稿はスキップ（上に表示済み）
            if history.index(entry) == 0 and _c == saved.strip():
                continue

            with st.expander(f"📅 {_d}"):
                st.markdown(
                    f"<div style='font-family:Inter,Noto Sans JP,sans-serif;font-size:0.85em;"
                    f"color:#b8b0a2;line-height:1.8;white-space:pre-wrap;'>{_c}</div>",
                    unsafe_allow_html=True,
                )


main()

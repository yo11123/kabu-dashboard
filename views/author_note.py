"""
相場観掲示板

アプリユーザーが自由に相場観を投稿できる掲示板。
投稿はGist/ローカルに永続化。
"""
import html as _html
from datetime import datetime
from hmac import compare_digest
from time import time as _time

import streamlit as st

from modules.persistence import _file_save, _file_load, _sync_to_gist
from modules.styles import apply_theme

apply_theme()

_BOARD_KEY = "market_board"
_MAX_POSTS = 200


def _load_posts() -> list[dict]:
    """投稿一覧を読み込む（新しい順）。"""
    posts = _file_load(_BOARD_KEY, [])
    if not isinstance(posts, list):
        return []
    return posts


def _save_post(name: str, content: str) -> None:
    """新しい投稿を保存する。"""
    posts = _load_posts()
    posts.insert(0, {
        "name": name,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    # 最大件数
    posts = posts[:_MAX_POSTS]
    _file_save(_BOARD_KEY, posts)
    _sync_to_gist()


def _delete_post(index: int, password: str) -> bool:
    """管理者パスワードで投稿を削除する。"""
    try:
        correct = st.secrets.get("AUTHOR_PASSWORD", "")
    except Exception:
        correct = ""
    if not correct or not compare_digest(password, correct):
        return False
    posts = _load_posts()
    if 0 <= index < len(posts):
        posts.pop(index)
        _file_save(_BOARD_KEY, posts)
        _sync_to_gist()
        return True
    return False


def _render_post(post: dict, index: int) -> None:
    """投稿1件を描画する。"""
    name = _html.escape(post.get("name", "匿名"))
    content = _html.escape(post.get("content", "")).replace("\n", "<br>")
    timestamp = post.get("timestamp", "")

    # 名前の色をハッシュから生成（ユーザーごとに色が変わる）
    colors = ["#8fb8a0", "#d4af37", "#58a6ff", "#d2a8ff", "#5ca08b", "#f47067", "#e3b341"]
    name_color = colors[hash(name) % len(colors)]

    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.4);
            border: 1px solid rgba(212,175,55,0.04);
            border-radius: 4px; padding: 14px 18px; margin-bottom: 8px;
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-weight:600;color:{name_color};font-size:0.9em;">{name}</span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:0.7em;color:#505868;">{timestamp}</span>
            </div>
            <div style="font-family:'Inter','Noto Sans JP',sans-serif;font-size:0.88em;
                 color:#b8b0a2;line-height:1.7;">
                {content}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>相場観掲示板</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-family:Inter,Noto Sans JP,sans-serif;font-size:0.85em;"
        "color:#6b7280;line-height:1.8;margin-bottom:16px;'>"
        "日本株市場の相場観を自由に投稿できる掲示板です。"
        "他のユーザーの見方を参考に、自分の投資判断に活かしてください。"
        "<br>あくまで個人の見解であり、投資助言ではありません。"
        "</div>",
        unsafe_allow_html=True,
    )

    posts = _load_posts()

    # ── 投稿フォーム ─────────────────────────────────────────
    with st.expander("✏️ 相場観を投稿する", expanded=not posts):
        col_name, col_submit = st.columns([3, 1])
        with col_name:
            user_name = st.text_input(
                "名前",
                placeholder="匿名",
                max_chars=20,
                key="board_name",
            )
        content = st.text_area(
            "相場観を入力",
            height=150,
            placeholder="例: VIXが30超で恐怖水準。ただしこういう時こそ優良株の押し目買いチャンス。特に自動車セクターに注目。",
            max_chars=1000,
            key="board_content",
        )
        with col_submit:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("投稿", type="primary", use_container_width=True, key="board_submit"):
                if content.strip():
                    _save_post(
                        name=user_name.strip() or "匿名",
                        content=content.strip(),
                    )
                    st.success("投稿しました！")
                    st.rerun()
                else:
                    st.warning("内容を入力してください")

    # ── 投稿一覧 ──────────────────────────────────────────────
    if not posts:
        st.info("まだ投稿がありません。最初の投稿をしてみましょう！")
    else:
        st.caption(f"{len(posts)} 件の投稿")

        for i, post in enumerate(posts):
            _render_post(post, i)

    # ── 管理者機能（削除）────────────────────────────────────
    try:
        has_admin = bool(st.secrets.get("AUTHOR_PASSWORD", ""))
    except Exception:
        has_admin = False

    if has_admin and posts:
        st.divider()
        with st.expander("🔧 管理者メニュー"):
            # ── レートリミット ──
            _rl = st.session_state.setdefault("_admin_rate", {"attempts": [], "locked_until": 0.0})
            _now = _time()
            if _now < _rl["locked_until"]:
                st.error("試行回数が上限に達しました。しばらく待ってから再度お試しください。")
            else:
                # 5分以上前の試行を除去
                _rl["attempts"] = [t for t in _rl["attempts"] if _now - t < 300]

                admin_pw = st.text_input("管理者パスワード", type="password", key="board_admin_pw")
                if admin_pw:
                    try:
                        correct = st.secrets.get("AUTHOR_PASSWORD", "")
                    except Exception:
                        correct = ""
                    if compare_digest(admin_pw, correct):
                        st.caption("削除したい投稿の番号を入力")
                        del_idx = st.number_input("投稿番号（0から）", min_value=0,
                                                  max_value=max(len(posts) - 1, 0), key="board_del_idx")
                        if st.button("削除", key="board_del_btn"):
                            if _delete_post(del_idx, admin_pw):
                                st.success("削除しました")
                                st.rerun()
                    else:
                        _rl["attempts"].append(_now)
                        if len(_rl["attempts"]) >= 5:
                            _rl["locked_until"] = _now + 300
                            st.error("試行回数が上限に達しました。5分後に再度お試しください。")
                        else:
                            st.error("パスワードが違います")


main()

"""
データ永続化ヘルパー
Cookie を使ってブラウザにデータを保存・復元する。
リロード・リブートしても消えない（max_age=1年）。
"""
import json
import streamlit as st
from streamlit_cookies_controller import CookieController

# Cookie の有効期限（秒）: 365日
_MAX_AGE = 365 * 24 * 3600

# シングルトン: 1ページにつき1つの CookieController
_controller_key = "__persistence_cookie_controller__"


def _get_controller() -> CookieController:
    """CookieController のシングルトンを返す。"""
    if _controller_key not in st.session_state:
        st.session_state[_controller_key] = CookieController()
    return st.session_state[_controller_key]


def save(key: str, data) -> None:
    """データを Cookie に JSON 保存する。"""
    ctrl = _get_controller()
    try:
        value = json.dumps(data, ensure_ascii=False)
        ctrl.set(key, value, max_age=_MAX_AGE)
    except Exception:
        pass


def load(key: str, default=None):
    """Cookie からデータを読み込む。なければ default を返す。"""
    ctrl = _get_controller()
    try:
        raw = ctrl.get(key)
        if raw is None:
            return default
        if isinstance(raw, str):
            return json.loads(raw)
        # 既にパース済みの場合
        return raw
    except Exception:
        return default


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """Cookie → session_state にロードする（session_state に未設定の場合のみ）。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = load(cookie_key, default)


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → Cookie に保存する。"""
    if session_key in st.session_state:
        save(cookie_key, st.session_state[session_key])

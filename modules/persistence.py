"""
データ永続化ヘルパー
Cookie を使ってブラウザにデータを保存・復元する。
リロード・リブートしても消えない（max_age=1年）。

使い方:
  - app.py で init_persistence() を pg.run() の前に呼ぶ
  - 各ページでは save() / load_into_session() を使う
"""
import json
import streamlit as st
from streamlit_cookies_controller import CookieController

# Cookie の有効期限（秒）: 365日
_MAX_AGE = 365 * 24 * 3600

# 永続化する全キーとデフォルト値の定義
PERSISTENT_KEYS = {
    "portfolio_holdings": [],
    "watchlist_data": [],
    "screener_conditions": [],
}

_CTRL_KEY = "__persistence_ctrl__"
_INITIALIZED_KEY = "__persistence_initialized__"


def _get_controller() -> CookieController:
    """CookieController のシングルトンを返す。"""
    if _CTRL_KEY not in st.session_state:
        st.session_state[_CTRL_KEY] = CookieController()
    return st.session_state[_CTRL_KEY]


def init_persistence() -> None:
    """
    app.py のエントリーポイントで呼ぶ。
    全 Cookie を一括で session_state にロードする。
    CookieController の JS がまだ準備できていなければ st.stop() で待つ。
    """
    if st.session_state.get(_INITIALIZED_KEY):
        return

    ctrl = _get_controller()

    # CookieController が JS 側で準備完了しているか確認
    all_cookies = ctrl.getAll()
    if all_cookies is None:
        # JS がまだロードされていない → 一度停止して再描画を待つ
        st.stop()
        return

    # 全永続キーを Cookie → session_state にロード
    for cookie_key, default in PERSISTENT_KEYS.items():
        session_key = cookie_key
        if session_key not in st.session_state:
            try:
                raw = all_cookies.get(cookie_key)
                if raw is not None:
                    if isinstance(raw, str):
                        st.session_state[session_key] = json.loads(raw)
                    else:
                        st.session_state[session_key] = raw
                else:
                    st.session_state[session_key] = default
            except Exception:
                st.session_state[session_key] = default

    st.session_state[_INITIALIZED_KEY] = True


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
        return raw
    except Exception:
        return default


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """Cookie → session_state にロードする（session_state に未設定の場合のみ）。
    init_persistence() で既にロード済みならスキップ。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = load(cookie_key, default)


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → Cookie に保存する。"""
    if session_key in st.session_state:
        save(cookie_key, st.session_state[session_key])

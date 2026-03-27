"""
データ永続化ヘルパー
Cookie を使ってブラウザにデータを保存・復元する。

仕組み:
  1. app.py で init_persistence() を pg.run() の前に毎回呼ぶ
  2. 初回: CookieController の JS がまだ未ロード → None → スキップ
  3. JS ロード完了で Streamlit が自動 rerun → 2回目で Cookie を読み取り
  4. session_state にデータを上書きして _LOADED フラグを立てる
  5. 以降は session_state から読むだけ（Cookie は書き込み時のみ使用）
"""
import json
import streamlit as st
from streamlit_cookies_controller import CookieController

_MAX_AGE = 365 * 24 * 3600  # 1年

# 永続化する全キーとデフォルト値
PERSISTENT_KEYS = {
    "portfolio_holdings": [],
    "watchlist_data": [],
    "screener_conditions": [],
}

_LOADED = "__persistence_loaded__"


def init_persistence() -> None:
    """
    app.py で pg.run() の前に毎回呼ぶ。
    Cookie の読み取りが成功するまで何度でもリトライする。
    成功したら session_state を上書きし、フラグを立てる。
    """
    # 既に正常にロード済みならスキップ
    if st.session_state.get(_LOADED):
        return

    # CookieController を毎回レンダリング（非表示コンポーネント）
    ctrl = CookieController()
    all_cookies = ctrl.getAll()

    if all_cookies is None:
        # JS がまだロードされていない。
        # ここでは何もせず return → Streamlit がコンポーネントをレンダリング
        # → JS ロード完了で自動 rerun → 次回呼び出しで読み取れる
        return

    # Cookie が読めた → session_state に上書き（デフォルト値を上書き）
    for cookie_key, default in PERSISTENT_KEYS.items():
        raw = all_cookies.get(cookie_key)
        if raw is not None:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                st.session_state[cookie_key] = parsed
            except Exception:
                if cookie_key not in st.session_state:
                    st.session_state[cookie_key] = default
        else:
            if cookie_key not in st.session_state:
                st.session_state[cookie_key] = default

    st.session_state[_LOADED] = True


def save(key: str, data) -> None:
    """データを Cookie に保存する。"""
    try:
        ctrl = CookieController()
        value = json.dumps(data, ensure_ascii=False)
        ctrl.set(key, value, max_age=_MAX_AGE)
    except Exception:
        pass


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → Cookie に保存する。"""
    if session_key in st.session_state:
        save(cookie_key, st.session_state[session_key])


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """session_state にキーがなければデフォルト値を設定する。
    Cookie からの読み取りは init_persistence() で一括実行済み。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = default

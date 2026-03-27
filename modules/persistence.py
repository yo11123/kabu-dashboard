"""
データ永続化ヘルパー
ファイル + Cookie の二重保存で、リロードでもリブートでもデータを保持。

- リロード: ファイルから即座に復元
- リブート: ファイルは消えるが Cookie から復元
"""
import json
import os
from datetime import date

import streamlit as st
from streamlit_cookies_controller import CookieController

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
os.makedirs(_DATA_DIR, exist_ok=True)

_MAX_AGE = 365 * 24 * 3600  # Cookie有効期限: 1年

# 永続化する全キーとデフォルト値
PERSISTENT_KEYS = {
    "portfolio_holdings": [],
    "watchlist_data": [],
    "screener_conditions": [],
}

# 当日限り有効なキー
DAILY_KEYS = {
    "portfolio_results": {},
}

_COOKIE_RESTORE_DONE = "__cookie_restore_done__"


# ─── ファイル操作 ─────────────────────────────────────────────────────────

def _file_path(key: str) -> str:
    return os.path.join(_DATA_DIR, f"{key}.json")


def _file_save(key: str, data) -> None:
    try:
        with open(_file_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _file_load(key: str, default=None):
    path = _file_path(key)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ─── Cookie 操作 ──────────────────────────────────────────────────────────

def _cookie_save(ctrl: CookieController, key: str, data) -> None:
    try:
        value = json.dumps(data, ensure_ascii=False)
        ctrl.set(key, value, max_age=_MAX_AGE)
    except Exception:
        pass


def _cookie_load_all(ctrl: CookieController) -> dict | None:
    """全 Cookie を取得。JS 未ロードなら None。"""
    try:
        return ctrl.getAll()
    except Exception:
        return None


# ─── 公開 API ─────────────────────────────────────────────────────────────

def init_persistence() -> None:
    """
    app.py で pg.run() の前に毎回呼ぶ。

    1. ファイルから全キーを session_state にロード
    2. ファイルが空（リブート後）なら Cookie から復元を試みる
    """
    # ── Step 1: ファイルからロード ──
    for key, default in PERSISTENT_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = _file_load(key, default)

    for key, default in DAILY_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = load_daily(key, default)

    # ── Step 2: ファイルが空ならCookieから復元 ──
    if st.session_state.get(_COOKIE_RESTORE_DONE):
        return

    # ファイルにデータがあるかチェック
    has_file_data = any(
        _file_load(key) not in (None, [], {})
        for key in PERSISTENT_KEYS
    )

    if has_file_data:
        # ファイルにデータあり（リロード）→ Cookie復元不要
        st.session_state[_COOKIE_RESTORE_DONE] = True
        return

    # ファイルが空（リブート後）→ Cookie から復元を試みる
    ctrl = CookieController()
    all_cookies = _cookie_load_all(ctrl)

    if all_cookies is None:
        # JS 未ロード → 次の rerun で再試行（フラグを立てない）
        return

    restored = False
    for key, default in PERSISTENT_KEYS.items():
        raw = all_cookies.get(key)
        if raw is not None:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if parsed and parsed != default:
                    st.session_state[key] = parsed
                    _file_save(key, parsed)  # ファイルにも保存
                    restored = True
            except Exception:
                pass

    # 当日限りキーも Cookie から復元
    for key, default in DAILY_KEYS.items():
        raw = all_cookies.get(key)
        if raw is not None:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict) and parsed.get("date") == date.today().isoformat():
                    st.session_state[key] = parsed.get("data", default)
                    _file_save(key, parsed)  # ファイルにも保存（日付付き）
                    restored = True
            except Exception:
                pass

    st.session_state[_COOKIE_RESTORE_DONE] = True

    if restored:
        st.rerun()


def save(key: str, data) -> None:
    """データをファイル + Cookie に二重保存。"""
    _file_save(key, data)
    # Cookie にもバックアップ
    try:
        ctrl = CookieController()
        _cookie_save(ctrl, key, data)
    except Exception:
        pass


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → ファイル + Cookie に保存。"""
    if session_key in st.session_state:
        save(cookie_key, st.session_state[session_key])


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """ファイル → session_state にロード（未設定の場合のみ）。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = _file_load(cookie_key, default)


def save_daily(key: str, data) -> None:
    """日付付きでファイル + Cookie に保存。当日分のみ有効。"""
    wrapped = {"date": date.today().isoformat(), "data": data}
    _file_save(key, wrapped)
    try:
        ctrl = CookieController()
        _cookie_save(ctrl, key, wrapped)
    except Exception:
        pass


def load_daily(key: str, default=None):
    """当日分のデータのみ読み込む。"""
    wrapped = _file_load(key)
    if wrapped is None:
        return default
    if not isinstance(wrapped, dict) or wrapped.get("date") != date.today().isoformat():
        return default
    return wrapped.get("data", default)

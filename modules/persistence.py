"""
データ永続化ヘルパー
サーバーサイド JSON ファイルで保存。リロードでも確実にデータが残る。
"""
import json
import os
from datetime import date

import streamlit as st

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
os.makedirs(_DATA_DIR, exist_ok=True)

# 永続化する全キーとデフォルト値（init_persistence で一括ロード）
PERSISTENT_KEYS = {
    "portfolio_holdings": [],
    "watchlist_data": [],
    "screener_conditions": [],
}

# 当日限り有効なキー（save_daily/load_daily で管理）
DAILY_KEYS = {
    "portfolio_results": {},
}


def _file_path(key: str) -> str:
    return os.path.join(_DATA_DIR, f"{key}.json")


def save(key: str, data) -> None:
    """データを JSON ファイルに保存。"""
    try:
        with open(_file_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def load(key: str, default=None):
    """JSON ファイルからデータを読み込む。"""
    path = _file_path(key)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def init_persistence() -> None:
    """全永続キーをファイルから session_state にロード。"""
    # 通常キー
    for key, default in PERSISTENT_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = load(key, default)

    # 当日限りキー
    for key, default in DAILY_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = load_daily(key, default)


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → ファイルに保存。"""
    if session_key in st.session_state:
        save(cookie_key, st.session_state[session_key])


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """ファイル → session_state にロード（未設定の場合のみ）。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = load(cookie_key, default)


def save_daily(key: str, data) -> None:
    """日付付きでデータを保存。当日分のみ有効。"""
    wrapped = {"date": date.today().isoformat(), "data": data}
    save(key, wrapped)


def load_daily(key: str, default=None):
    """当日分のデータのみ読み込む。日付が違えば default を返す。"""
    wrapped = load(key)
    if wrapped is None:
        return default
    if not isinstance(wrapped, dict) or wrapped.get("date") != date.today().isoformat():
        return default
    return wrapped.get("data", default)

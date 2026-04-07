"""
データ永続化ヘルパー
GitHub Gist をメインストレージとして使用。リブートしても絶対にデータが消えない。
ファイルはキャッシュとして併用（APIコール削減）。

セットアップ:
  1. https://github.com/settings/tokens で Personal Access Token を作成（gist権限のみ）
  2. Streamlit Cloud の secrets.toml に GITHUB_TOKEN = "ghp_xxxxx" を追加
"""
import json
import os
from datetime import date

import requests
import streamlit as st

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
os.makedirs(_DATA_DIR, exist_ok=True)

# 永続化する全キーとデフォルト値
PERSISTENT_KEYS = {
    "portfolio_holdings": [],
    "watchlist_data": [],
    "screener_conditions": [],
    "author_note": "",
    "author_note_history": [],
    "market_board": [],
    "ai_analysis_history": {},
    "youtube_summaries": [],
    "alerts": [],
}

DAILY_KEYS = {
    "portfolio_results": {},
}

_GIST_ID_FILE = os.path.join(_DATA_DIR, "_gist_id.txt")
_GIST_DESCRIPTION = "kabu-dashboard-user-data"


# ─── GitHub Token ─────────────────────────────────────────────────────────

def _get_github_token() -> str:
    try:
        return st.secrets.get("GITHUB_TOKEN", "")
    except Exception:
        return ""


# ─── Gist 操作 ────────────────────────────────────────────────────────────

def _gist_headers() -> dict:
    token = _get_github_token()
    if not token:
        return {}
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _get_gist_id() -> str:
    """保存済みの Gist ID を取得。なければ空文字。"""
    # ファイルキャッシュ
    if os.path.exists(_GIST_ID_FILE):
        with open(_GIST_ID_FILE, "r") as f:
            gid = f.read().strip()
            if gid:
                return gid
    # session_state
    return st.session_state.get("_gist_id", "")


def _save_gist_id(gist_id: str) -> None:
    st.session_state["_gist_id"] = gist_id
    try:
        with open(_GIST_ID_FILE, "w") as f:
            f.write(gist_id)
    except Exception:
        pass


def _gist_save_all(data: dict) -> bool:
    """全データを Gist に保存。成功なら True。"""
    headers = _gist_headers()
    if not headers:
        st.session_state["_gist_status"] = "❌ GITHUB_TOKEN が未設定です"
        return False

    content = json.dumps(data, ensure_ascii=False, indent=2)
    files = {"kabu_dashboard_data.json": {"content": content}}

    gist_id = _get_gist_id()

    try:
        if gist_id:
            # 更新
            resp = requests.patch(
                f"https://api.github.com/gists/{gist_id}",
                headers=headers,
                json={"files": files},
                timeout=10,
            )
            if resp.status_code == 200:
                st.session_state["_gist_status"] = f"✅ Gist保存成功 (ID: {gist_id[:8]}...)"
                return True
            # 404 なら Gist が削除されている → 新規作成にフォールバック

        # 新規作成
        resp = requests.post(
            "https://api.github.com/gists",
            headers=headers,
            json={
                "description": _GIST_DESCRIPTION,
                "public": False,
                "files": files,
            },
            timeout=10,
        )
        if resp.status_code == 201:
            new_id = resp.json()["id"]
            _save_gist_id(new_id)
            st.session_state["_gist_status"] = f"✅ Gist新規作成成功 (ID: {new_id[:8]}...)"
            return True
        st.session_state["_gist_status"] = f"❌ Gist保存失敗 (HTTP {resp.status_code}: {resp.text[:100]})"
    except Exception as e:
        st.session_state["_gist_status"] = f"❌ Gist例外: {str(e)[:100]}"
    return False


def _gist_load_all() -> dict | None:
    """Gist から全データを読み込む。"""
    headers = _gist_headers()
    if not headers:
        return None

    gist_id = _get_gist_id()

    # Gist ID が不明なら検索
    if not gist_id:
        gist_id = _find_gist()
        if gist_id:
            _save_gist_id(gist_id)

    if not gist_id:
        return None

    try:
        resp = requests.get(
            f"https://api.github.com/gists/{gist_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        files = resp.json().get("files", {})
        f = files.get("kabu_dashboard_data.json")
        if not f:
            return None
        return json.loads(f["content"])
    except Exception:
        return None


def _find_gist() -> str:
    """ユーザーの Gist から kabu-dashboard 用を検索。"""
    headers = _gist_headers()
    if not headers:
        return ""
    try:
        resp = requests.get(
            "https://api.github.com/gists",
            headers=headers,
            params={"per_page": 30},
            timeout=10,
        )
        if resp.status_code != 200:
            return ""
        for g in resp.json():
            if g.get("description") == _GIST_DESCRIPTION:
                return g["id"]
    except Exception:
        pass
    return ""


# ─── ファイルキャッシュ（APIコール削減）────────────────────────────────────

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


# ─── 公開 API ─────────────────────────────────────────────────────────────

def init_persistence() -> None:
    """app.py で pg.run() の前に呼ぶ。"""
    # 1. ファイルキャッシュからロード
    for key, default in PERSISTENT_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = _file_load(key, default)

    for key, default in DAILY_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = load_daily(key, default)

    # 2. ファイルが空（リブート後）なら Gist から復元
    has_file_data = any(
        _file_load(key) not in (None, [], {})
        for key in PERSISTENT_KEYS
    )

    restore_done = st.session_state.get("_gist_restore_done", False)

    st.session_state["_gist_status"] = (
        f"🔍 状態: files={'あり' if has_file_data else 'なし'}, "
        f"restore_done={restore_done}"
    )

    if not has_file_data and not restore_done:
        token = _get_github_token()
        gist_id = _get_gist_id()
        found_id = ""
        if not gist_id:
            found_id = _find_gist()

        gist_data = _gist_load_all()

        st.session_state["_gist_status"] = (
            f"🔍 復元試行: token={'あり' if token else 'なし'}, "
            f"gist_id={gist_id or found_id or 'なし'}, "
            f"データ={'あり' if gist_data else 'なし'}"
        )

        if gist_data:
            for key, default in PERSISTENT_KEYS.items():
                val = gist_data.get(key, default)
                if val and val != default:
                    st.session_state[key] = val
                    _file_save(key, val)

            for key, default in DAILY_KEYS.items():
                raw = gist_data.get(key)
                if raw and isinstance(raw, dict) and raw.get("date") == date.today().isoformat():
                    st.session_state[key] = raw.get("data", default)
                    _file_save(key, raw)

        st.session_state["_gist_restore_done"] = True


def save(key: str, data) -> None:
    """ファイル + Gist に保存。"""
    _file_save(key, data)
    # Gist に全データまとめて保存
    _sync_to_gist()


def save_from_session(cookie_key: str, session_key: str) -> None:
    """session_state → ファイル + Gist に保存。"""
    if session_key in st.session_state:
        _file_save(cookie_key, st.session_state[session_key])
        _sync_to_gist()


def _sync_to_gist() -> None:
    """全永続データを Gist に同期。"""
    all_data = {}
    for key in PERSISTENT_KEYS:
        all_data[key] = _file_load(key, PERSISTENT_KEYS[key])
    for key in DAILY_KEYS:
        raw = _file_load(key)
        if raw:
            all_data[key] = raw
    _gist_save_all(all_data)


def load_into_session(cookie_key: str, session_key: str, default=None) -> None:
    """ファイル → session_state にロード（未設定の場合のみ）。"""
    if session_key not in st.session_state:
        st.session_state[session_key] = _file_load(cookie_key, default)


def save_daily(key: str, data) -> None:
    """日付付きでファイル + Gist に保存。"""
    wrapped = {"date": date.today().isoformat(), "data": data}
    _file_save(key, wrapped)
    _sync_to_gist()


def load_daily(key: str, default=None):
    """当日分のデータのみ読み込む。"""
    wrapped = _file_load(key)
    if wrapped is None:
        return default
    if not isinstance(wrapped, dict) or wrapped.get("date") != date.today().isoformat():
        return default
    return wrapped.get("data", default)


def try_restore_from_cookies() -> None:
    """後方互換用。Gist方式では不要だが呼び出し元を壊さないために残す。"""
    pass


# ─── AI分析履歴 ─────────────────────────────────────────────────────────

_AI_HISTORY_KEY = "ai_analysis_history"
_MAX_HISTORY_DAYS = 30  # 最大30日分保持


def save_ai_history(ticker: str, result: dict) -> None:
    """AI分析結果を日付付きで履歴に追記する。"""
    today = date.today().isoformat()
    history = _file_load(_AI_HISTORY_KEY, {})
    if not isinstance(history, dict):
        history = {}

    if ticker not in history:
        history[ticker] = []

    # 同日の結果があれば上書き
    entries = [e for e in history[ticker] if e.get("date") != today]
    entries.append({
        "date": today,
        "overall_score": result.get("overall_score", 50),
        "technical_score": result.get("technical_score", 50),
        "fundamental_score": result.get("fundamental_score", 50),
        "news_score": result.get("news_score", 50),
        "judgment": result.get("judgment", "中立"),
        "overall_detail": result.get("overall_detail", ""),
        "opportunities": result.get("opportunities", []),
        "risks": result.get("risks", []),
        "provider": result.get("provider", ""),
    })

    # 日付降順ソートして最大30日分
    entries.sort(key=lambda x: x["date"], reverse=True)
    history[ticker] = entries[:_MAX_HISTORY_DAYS]

    _file_save(_AI_HISTORY_KEY, history)
    _sync_to_gist()


def load_ai_history(ticker: str) -> list[dict]:
    """指定銘柄のAI分析履歴を返す（日付降順）。"""
    history = _file_load(_AI_HISTORY_KEY, {})
    if not isinstance(history, dict):
        return []
    entries = history.get(ticker, [])
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


def load_all_ai_history() -> dict[str, list[dict]]:
    """全銘柄のAI分析履歴を返す。"""
    history = _file_load(_AI_HISTORY_KEY, {})
    return history if isinstance(history, dict) else {}

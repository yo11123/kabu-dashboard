"""
アラート管理モジュール
価格・RSI・出来高の条件アラートを作成・管理・判定する。
永続化は persistence.py 経由で GitHub Gist + ローカルファイルに保存。
"""
import uuid
from datetime import datetime

import yfinance as yf
import streamlit as st

from modules.persistence import save

# ─── 定数 ─────────────────────────────────────────────────────────────

CONDITION_TYPES = {
    "price_above": "株価が以上",
    "price_below": "株価が以下",
    "rsi_above": "RSIが以上",
    "rsi_below": "RSIが以下",
    "volume_spike": "出来高倍率が以上",
}

# 条件ごとのデフォルト閾値（UIヒント用）
CONDITION_DEFAULTS = {
    "price_above": 1000.0,
    "price_below": 1000.0,
    "rsi_above": 70.0,
    "rsi_below": 30.0,
    "volume_spike": 2.0,
}

# 売りサイド（赤）か買いサイド（緑）か
CONDITION_SIDE = {
    "price_above": "sell",   # 高値到達 → 利確
    "price_below": "buy",    # 安値到達 → 買い
    "rsi_above": "sell",     # 買われ過ぎ → 売り
    "rsi_below": "buy",      # 売られ過ぎ → 買い
    "volume_spike": "neutral",
}


# ─── CRUD 操作 ────────────────────────────────────────────────────────

def _ensure_alerts_key() -> None:
    """session_state に alerts キーがなければ初期化。"""
    if "alerts" not in st.session_state:
        st.session_state["alerts"] = []


def _save_alerts() -> None:
    """アラートを永続化。"""
    _ensure_alerts_key()
    save("alerts", st.session_state["alerts"])


def add_alert(ticker: str, name: str, condition_type: str, threshold: float) -> dict:
    """新しいアラートを作成して保存。"""
    _ensure_alerts_key()
    alert = {
        "id": str(uuid.uuid4()),
        "ticker": ticker,
        "name": name,
        "condition_type": condition_type,
        "threshold": threshold,
        "created_at": datetime.now().isoformat(),
        "triggered": False,
        "triggered_at": None,
        "active": True,
    }
    st.session_state["alerts"].append(alert)
    _save_alerts()
    return alert


def remove_alert(alert_id: str) -> None:
    """指定IDのアラートを削除。"""
    _ensure_alerts_key()
    st.session_state["alerts"] = [
        a for a in st.session_state["alerts"] if a["id"] != alert_id
    ]
    _save_alerts()


def get_alerts() -> list[dict]:
    """全アラートを返す。"""
    _ensure_alerts_key()
    return st.session_state["alerts"]


def get_active_alerts() -> list[dict]:
    """有効な（未トリガー）アラートを返す。"""
    return [a for a in get_alerts() if a["active"] and not a["triggered"]]


def get_triggered_alerts() -> list[dict]:
    """トリガー済みアラートを返す（新しい順）。"""
    triggered = [a for a in get_alerts() if a["triggered"]]
    triggered.sort(key=lambda x: x.get("triggered_at", ""), reverse=True)
    return triggered


def deactivate_alert(alert_id: str) -> None:
    """アラートを無効化（削除せずに非アクティブにする）。"""
    _ensure_alerts_key()
    for a in st.session_state["alerts"]:
        if a["id"] == alert_id:
            a["active"] = False
            break
    _save_alerts()


def reset_alert(alert_id: str) -> None:
    """トリガー済みアラートをリセットして再度有効化。"""
    _ensure_alerts_key()
    for a in st.session_state["alerts"]:
        if a["id"] == alert_id:
            a["triggered"] = False
            a["triggered_at"] = None
            a["active"] = True
            break
    _save_alerts()


# ─── RSI 計算 ────────────────────────────────────────────────────────

def _calc_rsi(hist, period: int = 14) -> float | None:
    """ヒストリカルデータからRSIを計算。"""
    if hist is None or len(hist) < period + 1:
        return None
    delta = hist["Close"].dropna().diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    loss = loss.replace(0, float("nan"))
    rs = gain / loss
    rsi_s = 100 - 100 / (1 + rs)
    val = rsi_s.iloc[-1]
    if val != val:  # NaN チェック
        return None
    return round(float(val), 1)


# ─── アラート判定 ─────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def _fetch_market_data(ticker: str) -> dict:
    """アラート判定用のマーケットデータを取得。"""
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = float(fi.last_price) if fi.last_price else 0
        if price != price:  # NaN
            price = 0

        hist = t.history(period="1mo")
        rsi = _calc_rsi(hist) if hist is not None and not hist.empty else None

        # 出来高比（直近5日 / 30日平均）
        vol_ratio = None
        if hist is not None and len(hist) >= 30:
            v5 = hist["Volume"].iloc[-5:].mean()
            v30 = hist["Volume"].iloc[-30:].mean()
            if v30 > 0:
                vol_ratio = round(float(v5 / v30), 2)

        return {"price": price, "rsi": rsi, "volume_ratio": vol_ratio}
    except Exception:
        return {"price": 0, "rsi": None, "volume_ratio": None}


def _evaluate_condition(data: dict, condition_type: str, threshold: float) -> bool:
    """単一条件を評価。True = 条件成立。"""
    if condition_type == "price_above":
        return data["price"] > 0 and data["price"] >= threshold
    elif condition_type == "price_below":
        return data["price"] > 0 and data["price"] <= threshold
    elif condition_type == "rsi_above":
        return data["rsi"] is not None and data["rsi"] >= threshold
    elif condition_type == "rsi_below":
        return data["rsi"] is not None and data["rsi"] <= threshold
    elif condition_type == "volume_spike":
        return data["volume_ratio"] is not None and data["volume_ratio"] >= threshold
    return False


def check_alerts() -> list[dict]:
    """
    全アクティブアラートをチェックし、新たにトリガーされたものを返す。
    トリガーされたアラートは自動で triggered=True に更新される。
    """
    _ensure_alerts_key()
    newly_triggered = []
    tickers_to_check = set()

    # チェック対象のティッカーを収集
    for a in st.session_state["alerts"]:
        if a["active"] and not a["triggered"]:
            tickers_to_check.add(a["ticker"])

    if not tickers_to_check:
        return []

    # 各ティッカーのデータを取得
    market_data = {}
    for ticker in tickers_to_check:
        market_data[ticker] = _fetch_market_data(ticker)

    # アラート判定
    changed = False
    for a in st.session_state["alerts"]:
        if not a["active"] or a["triggered"]:
            continue
        data = market_data.get(a["ticker"])
        if data is None:
            continue
        if _evaluate_condition(data, a["condition_type"], a["threshold"]):
            a["triggered"] = True
            a["triggered_at"] = datetime.now().isoformat()
            newly_triggered.append(a)
            changed = True

    if changed:
        _save_alerts()

    return newly_triggered


def get_alert_count_badge() -> int:
    """トリガー済みアラートの件数を返す（サイドバーバッジ用）。"""
    return len(get_triggered_alerts())


def format_condition(condition_type: str, threshold: float) -> str:
    """条件を日本語で表示用にフォーマット。"""
    label = CONDITION_TYPES.get(condition_type, condition_type)
    if condition_type in ("price_above", "price_below"):
        return f"{label} ¥{threshold:,.0f}"
    elif condition_type in ("rsi_above", "rsi_below"):
        return f"{label} {threshold:.0f}"
    elif condition_type == "volume_spike":
        return f"{label} {threshold:.1f}倍"
    return f"{label} {threshold}"

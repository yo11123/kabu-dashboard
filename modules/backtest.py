"""シンプルなバックテストエンジン（日本株向け）。

プリセット戦略やカスタム条件を使い、ロングオンリーのバックテストを実行する。
約定は翌日始値ベースで、現実的なシミュレーションを行う。
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# プリセット戦略
# ---------------------------------------------------------------------------

PRESET_STRATEGIES: dict[str, dict[str, str]] = {
    "RSI逆張り": {
        "description": "RSI30以下で買い、RSI70以上で売り",
        "buy_condition": "rsi <= 30",
        "sell_condition": "rsi >= 70",
    },
    "ゴールデンクロス": {
        "description": "SMA25がSMA75を上抜けで買い、下抜けで売り",
        "buy_condition": "golden_cross",
        "sell_condition": "death_cross",
    },
    "MACD": {
        "description": "MACDがシグナルを上抜けで買い、下抜けで売り",
        "buy_condition": "macd_cross_up",
        "sell_condition": "macd_cross_down",
    },
    "ボリンジャー逆張り": {
        "description": "BB-2σ以下で買い、BB+2σ以上で売り",
        "buy_condition": "bb_lower",
        "sell_condition": "bb_upper",
    },
    "出来高ブレイクアウト": {
        "description": "出来高が30日平均の2倍以上＋陽線で買い、RSI75以上で売り",
        "buy_condition": "volume_breakout",
        "sell_condition": "rsi >= 75",
    },
}

# ---------------------------------------------------------------------------
# 指標計算
# ---------------------------------------------------------------------------


def prepare_backtest_data(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame にバックテスト用の全指標・シグナル列を追加して返す。

    追加される列:
        rsi, sma25, sma75, macd, macd_signal, macd_histogram,
        bb_middle, bb_std, bb_upper_band, bb_lower_band,
        volume_ma30, volume_ratio,
        golden_cross, death_cross, macd_cross_up, macd_cross_down,
        bb_lower, bb_upper, volume_breakout,
        price_change_pct, sma25_above
    """
    df = df.copy()

    # --- RSI(14) ---
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - 100 / (1 + rs)

    # --- SMA(25), SMA(75) ---
    df["sma25"] = df["Close"].rolling(25).mean()
    df["sma75"] = df["Close"].rolling(75).mean()

    # --- MACD (12, 26, 9) ---
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    # --- Bollinger Bands (20, 2σ) ---
    df["bb_middle"] = df["Close"].rolling(20).mean()
    df["bb_std"] = df["Close"].rolling(20).std()
    df["bb_upper_band"] = df["bb_middle"] + 2 * df["bb_std"]
    df["bb_lower_band"] = df["bb_middle"] - 2 * df["bb_std"]

    # --- 出来高 MA(30) ---
    if "Volume" in df.columns:
        df["volume_ma30"] = df["Volume"].rolling(30).mean()
        df["volume_ratio"] = df["Volume"] / df["volume_ma30"].replace(0, np.nan)
    else:
        df["volume_ma30"] = np.nan
        df["volume_ratio"] = np.nan

    # --- ゴールデンクロス / デッドクロス ---
    sma25_prev = df["sma25"].shift(1)
    sma75_prev = df["sma75"].shift(1)
    df["golden_cross"] = (sma25_prev <= sma75_prev) & (df["sma25"] > df["sma75"])
    df["death_cross"] = (sma25_prev >= sma75_prev) & (df["sma25"] < df["sma75"])

    # --- MACD クロスシグナル ---
    macd_prev = df["macd"].shift(1)
    signal_prev = df["macd_signal"].shift(1)
    df["macd_cross_up"] = (macd_prev <= signal_prev) & (df["macd"] > df["macd_signal"])
    df["macd_cross_down"] = (macd_prev >= signal_prev) & (df["macd"] < df["macd_signal"])

    # --- BB タッチシグナル ---
    df["bb_lower"] = df["Close"] <= df["bb_lower_band"]
    df["bb_upper"] = df["Close"] >= df["bb_upper_band"]

    # --- BB σ値（中心からの標準偏差数） ---
    df["bb_sigma"] = (df["Close"] - df["bb_middle"]) / df["bb_std"].replace(0, np.nan)

    # --- 出来高ブレイクアウト (出来高2倍 + 陽線) ---
    is_bullish = df["Close"] > df["Open"]
    df["volume_breakout"] = (df["volume_ratio"] >= 2.0) & is_bullish

    # --- その他便利な列 ---
    df["price_change_pct"] = df["Close"].pct_change() * 100
    df["sma25_above"] = df["sma25"] > df["sma75"]

    return df


# ---------------------------------------------------------------------------
# 条件評価
# ---------------------------------------------------------------------------

# "field operator value" 形式をパースする正規表現
_CONDITION_RE = re.compile(
    r"^(\w+)\s*(<=|>=|<|>|==|!=)\s*([+-]?\d+(?:\.\d+)?)$"
)


def evaluate_condition(row: pd.Series, condition: str) -> bool:
    """条件文字列を DataFrame の1行に対して評価し、真偽値を返す。

    対応形式:
        - "rsi <= 30" 等の "field operator value" 形式
        - "golden_cross" 等のブール列名
    """
    condition = condition.strip()

    # --- ブール列名の場合 ---
    if condition in row.index and isinstance(row[condition], (bool, np.bool_)):
        return bool(row[condition])

    # --- field operator value 形式 ---
    m = _CONDITION_RE.match(condition)
    if m:
        field, op, value_str = m.groups()
        if field not in row.index:
            return False
        field_val = row[field]
        if pd.isna(field_val):
            return False
        value = float(value_str)
        if op == "<=":
            return float(field_val) <= value
        elif op == ">=":
            return float(field_val) >= value
        elif op == "<":
            return float(field_val) < value
        elif op == ">":
            return float(field_val) > value
        elif op == "==":
            return float(field_val) == value
        elif op == "!=":
            return float(field_val) != value

    logger.warning("条件を評価できません: %s", condition)
    return False


# ---------------------------------------------------------------------------
# カスタム条件パーサー
# ---------------------------------------------------------------------------


def evaluate_compound_condition(row: pd.Series, condition: str) -> bool:
    """AND/OR を含む複合条件を評価する。

    対応形式:
        - "rsi <= 30 AND macd_histogram > 0"
        - "rsi >= 70 OR bb_sigma > 2.0"
        - 単一条件も対応（従来の evaluate_condition と同等）
    """
    condition = condition.strip()

    # OR で分割（OR は AND より優先度が低い）
    if " OR " in condition:
        parts = [p.strip() for p in condition.split(" OR ")]
        return any(evaluate_compound_condition(row, p) for p in parts)

    # AND で分割
    if " AND " in condition:
        parts = [p.strip() for p in condition.split(" AND ")]
        return all(evaluate_compound_condition(row, p) for p in parts)

    # 単一条件
    return evaluate_condition(row, condition)


# ---------------------------------------------------------------------------
# 有効なフィールド・演算子一覧（LLM に提示用）
# ---------------------------------------------------------------------------

VALID_FIELDS = {
    "rsi", "macd_histogram", "bb_sigma", "volume_ratio",
    "sma25_above", "price_change_pct", "macd", "macd_signal",
    "golden_cross", "death_cross", "macd_cross_up", "macd_cross_down",
    "bb_lower", "bb_upper", "volume_breakout",
}
VALID_OPS = {"<=", ">=", "<", ">", "==", "!="}


def parse_custom_conditions(conditions: list[dict]) -> tuple[str, str]:
    """ユーザー定義条件リストから buy/sell 条件文字列を生成する。

    Parameters
    ----------
    conditions : list[dict]
        各要素は ``{"field": str, "operator": str, "value": number, "side": "buy"|"sell"}``。
        ``side`` が ``"buy"`` のものを買い条件、``"sell"`` のものを売り条件として結合する。
        複数条件は AND で結合される。

    Returns
    -------
    tuple[str, str]
        (buy_condition_str, sell_condition_str)
    """
    buy_parts: list[str] = []
    sell_parts: list[str] = []

    for cond in conditions:
        field = cond.get("field", "")
        op = cond.get("operator", "")
        value = cond.get("value", 0)
        side = cond.get("side", "buy")

        if field not in VALID_FIELDS:
            logger.warning("未対応のフィールド: %s", field)
            continue
        if op not in VALID_OPS:
            logger.warning("未対応の演算子: %s", op)
            continue

        expr = f"{field} {op} {value}"
        if side == "buy":
            buy_parts.append(expr)
        else:
            sell_parts.append(expr)

    buy_str = " AND ".join(buy_parts) if buy_parts else "rsi <= 30"
    sell_str = " AND ".join(sell_parts) if sell_parts else "rsi >= 70"

    return buy_str, sell_str


# ---------------------------------------------------------------------------
# リスク指標
# ---------------------------------------------------------------------------


def calc_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.001) -> float:
    """日次リターン系列から年率シャープレシオを計算する。

    Parameters
    ----------
    returns : pd.Series
        日次リターン（例: 0.01 = 1%）
    risk_free_rate : float
        年率リスクフリーレート（デフォルト 0.1%）

    Returns
    -------
    float
        年率シャープレシオ。データ不足時は 0.0。
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = returns - daily_rf
    return float(excess.mean() / excess.std() * np.sqrt(252))


def calc_max_drawdown(equity_curve: pd.Series) -> float:
    """資産曲線から最大ドローダウン（%）を計算する。

    Returns
    -------
    float
        最大ドローダウン（%、正の値で返す）。例: 15.3 は 15.3% の下落。
    """
    if equity_curve.empty:
        return 0.0
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100
    return float(abs(drawdown.min()))


# ---------------------------------------------------------------------------
# バックテスト実行
# ---------------------------------------------------------------------------


def run_backtest(
    df: pd.DataFrame,
    buy_condition: str,
    sell_condition: str,
    initial_capital: float = 1_000_000,
) -> dict[str, Any]:
    """ロングオンリーのバックテストを実行する。

    約定は **翌営業日の始値** で行い、現実的なシミュレーションとする。

    Parameters
    ----------
    df : pd.DataFrame
        ``prepare_backtest_data()`` で指標追加済みの OHLCV DataFrame。
        DatetimeIndex を持つことを想定。
    buy_condition : str
        買いシグナル条件文字列。
    sell_condition : str
        売りシグナル条件文字列。
    initial_capital : float
        初期資金（デフォルト 100万円）。

    Returns
    -------
    dict
        trades, equity_curve, total_return, win_rate, max_drawdown,
        sharpe_ratio, avg_holding_days, num_trades, profit_factor,
        buy_and_hold_return を含む辞書。
    """

    # --- データ検証 ---
    if len(df) < 2:
        logger.warning("バックテスト用データが不足しています（%d行）", len(df))
        return _empty_result(initial_capital)

    # 指標列が無ければ追加
    if "rsi" not in df.columns:
        df = prepare_backtest_data(df)

    trades: list[dict[str, Any]] = []
    equity_values: list[float] = []
    equity_dates: list = []

    capital = initial_capital
    position_open = False
    entry_price = 0.0
    entry_date = None
    shares = 0

    # 指標の安定に必要な最低限の期間（75日SMAが最長）をスキップ
    start_idx = max(75, 0)
    for i in range(start_idx, len(df) - 1):
        row = df.iloc[i]
        next_row = df.iloc[i + 1]
        current_date = df.index[i]
        next_date = df.index[i + 1]
        next_open = next_row["Open"]

        if not position_open:
            # --- 買いシグナル判定 ---
            if evaluate_compound_condition(row, buy_condition):
                if pd.isna(next_open) or next_open <= 0:
                    equity_values.append(capital)
                    equity_dates.append(current_date)
                    continue
                shares = int(capital // next_open)
                if shares > 0:
                    entry_price = next_open
                    entry_date = next_date
                    capital -= shares * entry_price
                    position_open = True
        else:
            # --- 売りシグナル判定 ---
            if evaluate_compound_condition(row, sell_condition):
                if pd.isna(next_open) or next_open <= 0:
                    equity_values.append(capital + shares * row["Close"])
                    equity_dates.append(current_date)
                    continue
                exit_price = next_open
                exit_date = next_date
                capital += shares * exit_price
                return_pct = (exit_price - entry_price) / entry_price * 100
                holding_days = (exit_date - entry_date).days if hasattr(exit_date - entry_date, "days") else 0

                trades.append(
                    {
                        "entry_date": entry_date,
                        "exit_date": exit_date,
                        "entry_price": float(entry_price),
                        "exit_price": float(exit_price),
                        "return_pct": float(return_pct),
                        "holding_days": int(holding_days),
                    }
                )
                position_open = False
                shares = 0

        # 資産曲線記録
        if position_open:
            mark_to_market = capital + shares * row["Close"]
        else:
            mark_to_market = capital
        equity_values.append(mark_to_market)
        equity_dates.append(current_date)

    # --- 最終日に未決済ポジションがあれば強制決済 ---
    last_row = df.iloc[-1]
    last_date = df.index[-1]
    if position_open:
        exit_price = float(last_row["Close"])
        return_pct = (exit_price - entry_price) / entry_price * 100
        holding_days = (last_date - entry_date).days if hasattr(last_date - entry_date, "days") else 0
        capital += shares * exit_price
        trades.append(
            {
                "entry_date": entry_date,
                "exit_date": last_date,
                "entry_price": float(entry_price),
                "exit_price": exit_price,
                "return_pct": float(return_pct),
                "holding_days": int(holding_days),
            }
        )
        position_open = False

    equity_values.append(capital)
    equity_dates.append(last_date)

    # --- 結果集計 ---
    equity_curve = pd.Series(equity_values, index=equity_dates, name="equity")
    # 重複インデックスがある場合は最後の値を保持
    equity_curve = equity_curve[~equity_curve.index.duplicated(keep="last")]

    total_return = (capital - initial_capital) / initial_capital * 100

    # 勝率
    if trades:
        wins = [t for t in trades if t["return_pct"] > 0]
        win_rate = len(wins) / len(trades) * 100
    else:
        win_rate = 0.0

    # 最大ドローダウン
    max_dd = calc_max_drawdown(equity_curve)

    # シャープレシオ（日次リターンから計算）
    daily_returns = equity_curve.pct_change().dropna()
    sharpe = calc_sharpe_ratio(daily_returns)

    # 平均保有日数
    if trades:
        avg_holding = sum(t["holding_days"] for t in trades) / len(trades)
    else:
        avg_holding = 0.0

    # プロフィットファクター
    gross_profit = sum(t["return_pct"] for t in trades if t["return_pct"] > 0)
    gross_loss = abs(sum(t["return_pct"] for t in trades if t["return_pct"] <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    # バイ・アンド・ホールド（ベンチマーク）
    close_clean = df["Close"].dropna()
    first_close = float(close_clean.iloc[0]) if not close_clean.empty else 1
    last_close = float(close_clean.iloc[-1]) if not close_clean.empty else 1
    buy_and_hold_return = (last_close - first_close) / first_close * 100
    buy_and_hold_curve = (close_clean / first_close) * initial_capital

    if not trades:
        logger.warning("バックテスト結果: 取引が発生しませんでした。条件を見直してください。")

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "buy_and_hold_curve": buy_and_hold_curve,
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "max_drawdown": float(max_dd),
        "sharpe_ratio": float(sharpe),
        "avg_holding_days": float(avg_holding),
        "num_trades": len(trades),
        "profit_factor": float(profit_factor),
        "buy_and_hold_return": float(buy_and_hold_return),
    }


def _empty_result(initial_capital: float) -> dict[str, Any]:
    """データ不足時の空の結果辞書を返す。"""
    return {
        "trades": [],
        "equity_curve": pd.Series(dtype=float),
        "buy_and_hold_curve": pd.Series(dtype=float),
        "total_return": 0.0,
        "win_rate": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "avg_holding_days": 0.0,
        "num_trades": 0,
        "profit_factor": 0.0,
        "buy_and_hold_return": 0.0,
    }

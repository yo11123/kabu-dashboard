"""
pandas-ta ラッパーモジュール

pandas-ta ライブラリを使って 130+ のテクニカル指標を一括計算する。
既存の _calc_features() との後方互換性を保ちつつ、指標数を大幅に拡張する。

使い方:
    from modules.ta_features import calc_ta_features
    features = calc_ta_features(df, mode="full")   # 130+ 指標
    features = calc_ta_features(df, mode="quick")  #  ~30 指標（高速スクリーニング用）
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None  # type: ignore


# ─── ヘルパー ──────────────────────────────────────────────────────────────

def _add(parts: list[pd.DataFrame], result: Any, name: str | None = None,
         prefix: str = "") -> None:
    """pandas-ta の返り値（Series/DataFrame/tuple/None）を parts リストに追加する。

    DataFrame の断片化を避けるため、最終的に pd.concat で一括結合する。
    """
    if result is None:
        return

    # ichimoku は (df, span_df) のタプルを返す
    if isinstance(result, tuple):
        for i, item in enumerate(result):
            _add(parts, item, name=f"{name}_{i}" if name else None, prefix=prefix)
        return

    if isinstance(result, pd.DataFrame):
        if prefix:
            result = result.rename(columns=lambda c: f"{prefix}{c}")
        parts.append(result)
    elif isinstance(result, pd.Series):
        col_name = name or result.name or "unnamed"
        if prefix:
            col_name = f"{prefix}{col_name}"
        parts.append(result.to_frame(col_name))


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """カラム名をML向けに正規化する（小文字、空白→_、特殊文字除去）。"""
    new_cols: dict[str, str] = {}
    seen: set[str] = set()
    for col in df.columns:
        c = str(col).lower().strip()
        c = c.replace(" ", "_").replace("-", "_").replace(".", "_")
        c = c.replace("%", "pct").replace("(", "").replace(")", "")
        c = c.replace("[", "").replace("]", "").replace("/", "_")
        # 重複回避
        base = c
        counter = 2
        while c in seen:
            c = f"{base}_{counter}"
            counter += 1
        seen.add(c)
        new_cols[col] = c
    return df.rename(columns=new_cols)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """NaN / inf をクリーンアップする。"""
    df = df.ffill().fillna(0)
    df = df.replace([np.inf, -np.inf], 0)
    return df


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV カラムを正規化して返す。yfinance 出力の揺れに対応。"""
    out = pd.DataFrame(index=df.index)

    # カラム名の大文字小文字の揺れを吸収
    col_map: dict[str, str] = {}
    for c in df.columns:
        cl = str(c).lower().strip()
        if cl == "open":
            col_map["Open"] = c
        elif cl == "high":
            col_map["High"] = c
        elif cl == "low":
            col_map["Low"] = c
        elif cl in ("close", "adj close", "adj_close"):
            col_map["Close"] = c
        elif cl == "volume":
            col_map["Volume"] = c

    out["Open"] = df[col_map.get("Open", "Open")].copy() if "Open" in col_map else df.iloc[:, 0]
    out["High"] = df[col_map.get("High", "High")].copy() if "High" in col_map else out["Open"]
    out["Low"] = df[col_map.get("Low", "Low")].copy() if "Low" in col_map else out["Open"]
    out["Close"] = df[col_map.get("Close", "Close")].copy() if "Close" in col_map else out["Open"]
    out["Volume"] = df[col_map.get("Volume", "Volume")].copy() if "Volume" in col_map else pd.Series(0, index=df.index)

    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.ffill().fillna(0)
    return out


def _build(parts: list[pd.DataFrame], index: pd.Index) -> pd.DataFrame:
    """parts リストを一括結合して DataFrame を構築する。"""
    if not parts:
        return pd.DataFrame(index=index)
    # reindex して index を揃えてから concat（ichimoku の span などで長さが変わる場合の対策）
    aligned = []
    for p in parts:
        if len(p) != len(index) or not p.index.equals(index):
            p = p.reindex(index)
        aligned.append(p)
    return pd.concat(aligned, axis=1)


# ─── Quick モード（~30 指標）─────────────────────────────────────────────

def _calc_quick(df: pd.DataFrame) -> pd.DataFrame:
    """主要 ~30 指標のみ高速に計算する。"""
    ohlcv = _ensure_ohlcv(df)
    close = ohlcv["Close"]
    high = ohlcv["High"]
    low = ohlcv["Low"]
    volume = ohlcv["Volume"]
    parts: list[pd.DataFrame] = []

    # ── モメンタム ──────────────────────────────────────────
    _add(parts, ta.rsi(close, length=14), "rsi_14")
    _add(parts, ta.rsi(close, length=5), "rsi_5")
    _add(parts, ta.macd(close, fast=12, slow=26, signal=9))
    _add(parts, ta.stoch(high, low, close, k=14, d=3))
    _add(parts, ta.cci(high, low, close, length=20), "cci_20")
    _add(parts, ta.willr(high, low, close, length=14), "williams_r_14")

    # ── トレンド ────────────────────────────────────────────
    _add(parts, ta.adx(high, low, close, length=14))

    sma_parts: dict[str, pd.Series] = {}
    for period in [5, 25, 75, 200]:
        sma = ta.sma(close, length=period)
        if sma is not None:
            sma_parts[f"sma{period}_dev"] = (close - sma) / sma * 100
    if sma_parts:
        parts.append(pd.DataFrame(sma_parts, index=ohlcv.index))

    ema12 = ta.ema(close, length=12)
    ema26 = ta.ema(close, length=26)
    if ema12 is not None and ema26 is not None:
        parts.append(((ema12 - ema26) / close * 100).to_frame("ema12_26_diff"))

    # ── ボラティリティ ──────────────────────────────────────
    bb_df = ta.bbands(close, length=20, std=2)
    if bb_df is not None:
        parts.append(bb_df)
        mid_col = [c for c in bb_df.columns if "mid" in c.lower() or "bbm" in c.lower()]
        upper_col = [c for c in bb_df.columns if "upper" in c.lower() or "bbu" in c.lower()]
        lower_col = [c for c in bb_df.columns if "lower" in c.lower() or "bbl" in c.lower()]
        if mid_col and upper_col and lower_col:
            bw = bb_df[upper_col[0]] - bb_df[lower_col[0]]
            bb_extra = pd.DataFrame({
                "bb_position": (close - bb_df[mid_col[0]]) / (bw / 4).replace(0, np.nan),
                "bb_width": bw / bb_df[mid_col[0]].replace(0, np.nan) * 100,
            }, index=ohlcv.index)
            parts.append(bb_extra)

    atr14 = ta.atr(high, low, close, length=14)
    if atr14 is not None:
        parts.append(pd.DataFrame({
            "atr_14": atr14,
            "atr_14_pct": atr14 / close * 100,
        }, index=ohlcv.index))

    # ── 出来高 ──────────────────────────────────────────────
    if volume.sum() > 0:
        obv = ta.obv(close, volume)
        if obv is not None:
            obv_sma = obv.rolling(20).mean()
            parts.append(pd.DataFrame({
                "obv": obv,
                "obv_dev": (obv - obv_sma) / obv_sma.abs().replace(0, np.nan) * 100,
            }, index=ohlcv.index))
        _add(parts, ta.mfi(high, low, close, volume, length=14), "mfi_14")

    # ── リターン・ボラティリティ（既存互換）─────────────────
    ret_dict: dict[str, pd.Series] = {}
    for d in [1, 2, 3, 5, 10, 20, 60]:
        ret_dict[f"return_{d}d"] = close.pct_change(d) * 100
    ret_dict["volatility_20d"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    ret_dict["volatility_5d"] = close.pct_change().rolling(5).std() * np.sqrt(252) * 100
    parts.append(pd.DataFrame(ret_dict, index=ohlcv.index))

    return _build(parts, ohlcv.index)


# ─── Full モード（130+ 指標）─────────────────────────────────────────────

def _calc_full(df: pd.DataFrame) -> pd.DataFrame:
    """130+ テクニカル指標を網羅的に計算する。"""
    ohlcv = _ensure_ohlcv(df)
    close = ohlcv["Close"]
    high = ohlcv["High"]
    low = ohlcv["Low"]
    opn = ohlcv["Open"]
    volume = ohlcv["Volume"]
    parts: list[pd.DataFrame] = []

    # ==================================================================
    #  Group 1: モメンタム (Momentum)
    # ==================================================================
    for length in [5, 14, 21]:
        _add(parts, ta.rsi(close, length=length), f"rsi_{length}")

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is not None:
        parts.append(macd_df)
        # MACD ヒストグラムの変化率（既存互換）
        hist_col = [c for c in macd_df.columns if "hist" in c.lower() or "macdh" in c.lower()]
        if hist_col:
            parts.append(macd_df[hist_col[0]].diff().to_frame("macd_hist_diff"))

    for k_period in [14, 9, 5]:
        _add(parts, ta.stoch(high, low, close, k=k_period, d=3), prefix=f"stoch_{k_period}_")

    for length in [14, 20]:
        _add(parts, ta.cci(high, low, close, length=length), f"cci_{length}")

    for length in [14, 28]:
        _add(parts, ta.willr(high, low, close, length=length), f"williams_r_{length}")

    _add(parts, ta.roc(close, length=5), "roc_5")
    _add(parts, ta.roc(close, length=10), "roc_10")
    _add(parts, ta.roc(close, length=20), "roc_20")

    _add(parts, ta.mom(close, length=10), "mom_10")
    _add(parts, ta.mom(close, length=20), "mom_20")

    _add(parts, ta.ao(high, low, fast=5, slow=34), "awesome_osc")

    # PPO (Percentage Price Oscillator)
    _add(parts, ta.ppo(close, fast=12, slow=26, signal=9))

    # UO (Ultimate Oscillator)
    _add(parts, ta.uo(high, low, close), "uo")

    # TSI (True Strength Index)
    _add(parts, ta.tsi(close))

    # Fisher Transform
    _add(parts, ta.fisher(high, low, length=9))

    # ==================================================================
    #  Group 2: トレンド (Trend)
    # ==================================================================
    _add(parts, ta.adx(high, low, close, length=14))

    # Aroon
    _add(parts, ta.aroon(high, low, length=25))

    # SMA 乖離率（複数期間）
    sma_dict: dict[str, pd.Series] = {}
    sma25: pd.Series | None = None
    sma75: pd.Series | None = None
    for period in [5, 10, 20, 25, 50, 75, 100, 200]:
        sma = ta.sma(close, length=period)
        if sma is not None:
            sma_dict[f"sma{period}_dev"] = (close - sma) / sma * 100
            if period == 25:
                sma25 = sma
            elif period == 75:
                sma75 = sma
    if sma_dict:
        parts.append(pd.DataFrame(sma_dict, index=ohlcv.index))

    # EMA 乖離率
    ema_dict: dict[str, pd.Series] = {}
    for period in [5, 12, 20, 26, 50, 100, 200]:
        ema = ta.ema(close, length=period)
        if ema is not None:
            ema_dict[f"ema{period}_dev"] = (close - ema) / ema * 100
    if ema_dict:
        parts.append(pd.DataFrame(ema_dict, index=ohlcv.index))

    # SMA の傾き & クロスギャップ（既存互換）
    slope_dict: dict[str, pd.Series] = {}
    if sma25 is not None:
        slope_dict["sma25_slope"] = sma25.pct_change(5) * 100
    if sma75 is not None:
        slope_dict["sma75_slope"] = sma75.pct_change(10) * 100
    if sma25 is not None and sma75 is not None:
        slope_dict["sma_cross_gap"] = (sma25 - sma75) / sma75.replace(0, np.nan) * 100
    if slope_dict:
        parts.append(pd.DataFrame(slope_dict, index=ohlcv.index))

    # WMA / DEMA / TEMA / KAMA / T3 乖離率
    ma_extra: dict[str, pd.Series] = {}
    wma10 = ta.wma(close, length=10)
    if wma10 is not None:
        ma_extra["wma10_dev"] = (close - wma10) / wma10 * 100
    dema20 = ta.dema(close, length=20)
    if dema20 is not None:
        ma_extra["dema20_dev"] = (close - dema20) / dema20 * 100
    tema20 = ta.tema(close, length=20)
    if tema20 is not None:
        ma_extra["tema20_dev"] = (close - tema20) / tema20 * 100
    kama10 = ta.kama(close, length=10)
    if kama10 is not None:
        ma_extra["kama10_dev"] = (close - kama10) / kama10 * 100
    t3_10 = ta.t3(close, length=10)
    if t3_10 is not None:
        ma_extra["t3_10_dev"] = (close - t3_10) / t3_10 * 100
    if ma_extra:
        parts.append(pd.DataFrame(ma_extra, index=ohlcv.index))

    # PSAR (Parabolic SAR)
    psar_df = ta.psar(high, low, close)
    if psar_df is not None:
        psar_cols = [c for c in psar_df.columns if "long" in c.lower() or "short" in c.lower()]
        if psar_cols:
            parts.append(psar_df[psar_cols])
        psar_extra: dict[str, pd.Series] = {}
        long_col = [c for c in psar_df.columns if "long" in c.lower()]
        short_col = [c for c in psar_df.columns if "short" in c.lower()]
        if long_col:
            psar_extra["psar_long_dev"] = (close - psar_df[long_col[0]].fillna(0)) / close * 100
        if short_col:
            psar_extra["psar_short_dev"] = (close - psar_df[short_col[0]].fillna(0)) / close * 100
        if psar_extra:
            parts.append(pd.DataFrame(psar_extra, index=ohlcv.index))

    # 一目均衡表 (Ichimoku)
    try:
        ichimoku_result = ta.ichimoku(high, low, close, tenkan=9, kijun=26, senkou=52)
        if ichimoku_result is not None:
            if isinstance(ichimoku_result, tuple):
                ich_df = ichimoku_result[0]
            else:
                ich_df = ichimoku_result
            if isinstance(ich_df, pd.DataFrame):
                # reindex して長さを揃える
                ich_df = ich_df.reindex(ohlcv.index)
                parts.append(ich_df)
                # 既存互換: 転換線/基準線乖離
                ich_extra: dict[str, pd.Series] = {}
                tenkan_col = [c for c in ich_df.columns if "tenkan" in c.lower() or "its" in c.lower()]
                kijun_col = [c for c in ich_df.columns if "kijun" in c.lower() or "iks" in c.lower()]
                if tenkan_col:
                    t = ich_df[tenkan_col[0]]
                    ich_extra["ichimoku_tenkan_dev"] = (close - t) / t.replace(0, np.nan) * 100
                if kijun_col:
                    k = ich_df[kijun_col[0]]
                    ich_extra["ichimoku_kijun_dev"] = (close - k) / k.replace(0, np.nan) * 100
                if ich_extra:
                    parts.append(pd.DataFrame(ich_extra, index=ohlcv.index))
    except Exception:
        pass  # 一目均衡表はデータ不足でエラーになることがある

    # TRIX
    _add(parts, ta.trix(close, length=15), "trix_15")

    # CG (Center of Gravity)
    _add(parts, ta.cg(close, length=10), "cg_10")

    # ==================================================================
    #  Group 3: ボラティリティ (Volatility)
    # ==================================================================

    # ボリンジャーバンド（複数期間）
    for length in [20, 10]:
        bb_df = ta.bbands(close, length=length, std=2)
        if bb_df is not None:
            parts.append(bb_df.rename(columns=lambda c: f"{c}_{length}"))

    # BB ポジション・幅（既存互換、期間20）
    bb20 = ta.bbands(close, length=20, std=2)
    if bb20 is not None:
        mid_col = [c for c in bb20.columns if "mid" in c.lower() or "bbm" in c.lower()]
        upper_col = [c for c in bb20.columns if "upper" in c.lower() or "bbu" in c.lower()]
        lower_col = [c for c in bb20.columns if "lower" in c.lower() or "bbl" in c.lower()]
        if mid_col and upper_col and lower_col:
            bw = bb20[upper_col[0]] - bb20[lower_col[0]]
            bb_pos = (close - bb20[mid_col[0]]) / (bw / 4).replace(0, np.nan)
            bb_w = bw / bb20[mid_col[0]].replace(0, np.nan) * 100
            parts.append(pd.DataFrame({
                "bb_position": bb_pos,
                "bb_width": bb_w,
                "bb_width_change": bb_w.pct_change(5) * 100,
            }, index=ohlcv.index))

    # ATR（複数期間）
    atr_dict: dict[str, pd.Series] = {}
    for length in [7, 14, 21]:
        atr = ta.atr(high, low, close, length=length)
        if atr is not None:
            atr_dict[f"atr_{length}"] = atr
            atr_dict[f"atr_{length}_pct"] = atr / close * 100
    if atr_dict:
        parts.append(pd.DataFrame(atr_dict, index=ohlcv.index))

    # NATR (Normalized ATR)
    _add(parts, ta.natr(high, low, close, length=14), "natr_14")

    # ケルトナーチャネル (Keltner Channel)
    kc_df = ta.kc(high, low, close, length=20, scalar=1.5)
    if kc_df is not None:
        parts.append(kc_df)
        kc_upper = [c for c in kc_df.columns if "upper" in c.lower() or "kcu" in c.lower()]
        kc_lower = [c for c in kc_df.columns if "lower" in c.lower() or "kcl" in c.lower()]
        if kc_upper and kc_lower:
            kc_range = kc_df[kc_upper[0]] - kc_df[kc_lower[0]]
            parts.append(((close - kc_df[kc_lower[0]]) / kc_range.replace(0, np.nan)).to_frame("kc_position"))

    # ドンチャンチャネル (Donchian Channel)
    dc_dict: dict[str, pd.Series] = {}
    for period in [10, 20, 50]:
        dc_df = ta.donchian(high, low, lower_length=period, upper_length=period)
        if dc_df is not None:
            dc_upper = [c for c in dc_df.columns if "upper" in c.lower() or "dcu" in c.lower()]
            dc_lower = [c for c in dc_df.columns if "lower" in c.lower() or "dcl" in c.lower()]
            if dc_upper and dc_lower:
                dc_range = dc_df[dc_upper[0]] - dc_df[dc_lower[0]]
                dc_dict[f"donchian_pos_{period}"] = (close - dc_df[dc_lower[0]]) / dc_range.replace(0, np.nan)
                dc_dict[f"donchian_width_{period}"] = dc_range / close * 100
    if dc_dict:
        parts.append(pd.DataFrame(dc_dict, index=ohlcv.index))

    # Ulcer Index
    _add(parts, ta.ui(close, length=10), "ulcer_index_10")

    # Historical Volatility（ローリング標準偏差ベース）
    pct = close.pct_change()
    vol_dict: dict[str, pd.Series] = {}
    vol_dict["volatility_5d"] = pct.rolling(5).std() * np.sqrt(252) * 100
    vol_dict["volatility_10d"] = pct.rolling(10).std() * np.sqrt(252) * 100
    vol_dict["volatility_20d"] = pct.rolling(20).std() * np.sqrt(252) * 100
    vol_dict["volatility_60d"] = pct.rolling(60).std() * np.sqrt(252) * 100
    vol_5 = vol_dict["volatility_5d"]
    vol_20 = vol_dict["volatility_20d"]
    vol_dict["vol_change"] = vol_5 - vol_20
    vol_dict["vol_ratio_5_20"] = vol_5 / vol_20.replace(0, np.nan)
    parts.append(pd.DataFrame(vol_dict, index=ohlcv.index))

    # Mass Index
    _add(parts, ta.massi(high, low, fast=9, slow=25), "mass_index")

    # ==================================================================
    #  Group 4: 出来高 (Volume)
    # ==================================================================
    has_volume = volume.sum() > 0

    if has_volume:
        obv = ta.obv(close, volume)
        if obv is not None:
            obv_sma20 = obv.rolling(20).mean()
            parts.append(pd.DataFrame({
                "obv": obv,
                "obv_dev": (obv - obv_sma20) / obv_sma20.abs().replace(0, np.nan) * 100,
                "obv_slope": obv.pct_change(5) * 100,
            }, index=ohlcv.index))

        _add(parts, ta.mfi(high, low, close, volume, length=14), "mfi_14")

        ad = ta.ad(high, low, close, volume)
        if ad is not None:
            parts.append(pd.DataFrame({
                "ad_line": ad,
                "ad_slope": ad.pct_change(5) * 100,
            }, index=ohlcv.index))

        _add(parts, ta.cmf(high, low, close, volume, length=20), "cmf_20")
        _add(parts, ta.efi(close, volume, length=13), "efi_13")

        # VWAP（日次データではローリングVWAPを使用）
        vwap_val = (close * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)
        vol_ma20 = volume.rolling(20).mean()
        up_mask = close > opn
        up_vol = (volume * up_mask.astype(float)).rolling(10).mean()
        dn_vol = (volume * (~up_mask).astype(float)).rolling(10).mean()
        parts.append(pd.DataFrame({
            "vwap_dev": (close - vwap_val) / vwap_val * 100,
            "volume_ratio": volume / vol_ma20.replace(0, np.nan),
            "volume_change_5d": volume.rolling(5).mean() / vol_ma20.replace(0, np.nan),
            "volume_up_dn_ratio": up_vol / dn_vol.replace(0, np.nan),
        }, index=ohlcv.index))

        # NVI / PVI (Negative/Positive Volume Index)
        # これらは DataFrame を返す場合があるので _add を使う
        _add(parts, ta.nvi(close, volume), "nvi")
        _add(parts, ta.pvi(close, volume), "pvi")

    # ==================================================================
    #  Group 5: 統計 (Statistics)
    # ==================================================================
    for length in [10, 20, 60]:
        _add(parts, ta.variance(close, length=length), f"variance_{length}")

    _add(parts, ta.skew(close, length=30), "skew_30")
    _add(parts, ta.kurtosis(close, length=30), "kurtosis_30")

    _add(parts, ta.zscore(close, length=20), "zscore_20")
    _add(parts, ta.zscore(close, length=60), "zscore_60")

    _add(parts, ta.quantile(close, length=20), "quantile_20")
    _add(parts, ta.quantile(close, length=60), "quantile_60")

    _add(parts, ta.entropy(close, length=10), "entropy_10")

    # ==================================================================
    #  Group 6: リターン・既存互換特徴量
    # ==================================================================
    compat_dict: dict[str, pd.Series] = {}
    for d in [1, 2, 3, 5, 10, 20, 60]:
        compat_dict[f"return_{d}d"] = close.pct_change(d) * 100

    compat_dict["from_52w_high"] = (close / close.rolling(252).max() - 1) * 100
    compat_dict["from_52w_low"] = (close / close.rolling(252).min() - 1) * 100

    compat_dict["autocorr_5d"] = close.pct_change().rolling(20).apply(
        lambda x: x.autocorr(lag=1) if len(x.dropna()) > 5 else np.nan, raw=False
    )

    compat_dict["up_day_ratio_10d"] = (close.diff() > 0).astype(float).rolling(10).mean()
    compat_dict["up_day_ratio_20d"] = (close.diff() > 0).astype(float).rolling(20).mean()

    ret20 = close.pct_change().rolling(20)
    compat_dict["sharpe_20d"] = ret20.mean() / ret20.std().replace(0, np.nan) * np.sqrt(252)

    compat_dict["hurst_proxy"] = close.pct_change().rolling(60).apply(
        lambda x: np.log(x.std()) / np.log(len(x)) if x.std() > 0 else np.nan, raw=False
    )

    compat_dict["candle_body"] = (close - opn) / opn * 100
    body = compat_dict["candle_body"]
    compat_dict["candle_body_avg5"] = body.rolling(5).mean()
    compat_dict["upper_shadow"] = (high - pd.concat([close, opn], axis=1).max(axis=1)) / close * 100
    compat_dict["lower_shadow"] = (pd.concat([close, opn], axis=1).min(axis=1) - low) / close * 100

    parts.append(pd.DataFrame(compat_dict, index=ohlcv.index))

    # ゴールデンクロス・デッドクロス（既存互換）
    if sma25 is not None and sma75 is not None:
        parts.append(pd.DataFrame({
            "golden_cross_5_25": ((sma25 > sma75) & (sma25.shift(1) <= sma75.shift(1))).astype(int),
            "dead_cross_5_25": ((sma25 < sma75) & (sma25.shift(1) >= sma75.shift(1))).astype(int),
        }, index=ohlcv.index))

    # カレンダー特徴量（既存互換）
    parts.append(pd.DataFrame({
        "weekday": df.index.dayofweek,
        "month": df.index.month,
    }, index=ohlcv.index))

    # ==================================================================
    #  Group 7: キャンドルスティックパターン
    # ==================================================================
    try:
        _add(parts, ta.cdl_doji(opn, high, low, close), "cdl_doji")
    except (AttributeError, TypeError):
        pass

    try:
        _add(parts, ta.cdl_inside(opn, high, low, close), "cdl_inside")
    except (AttributeError, TypeError):
        pass

    # ==================================================================
    #  Group 8: Squeeze (BBとKCの関係)
    # ==================================================================
    _add(parts, ta.squeeze(high, low, close, bb_length=20, bb_std=2,
                           kc_length=20, kc_scalar=1.5))

    return _build(parts, ohlcv.index)


# ─── メイン公開関数 ────────────────────────────────────────────────────────

def calc_ta_features(
    df: pd.DataFrame,
    mode: str = "full",
    *,
    quick: bool | None = None,
    full: bool | None = None,
) -> pd.DataFrame:
    """pandas-ta でテクニカル指標を一括計算する。

    Args:
        df: OHLCV データ（Open, High, Low, Close, Volume）。
            yfinance で取得した日本株データをそのまま渡せる。
        mode: "quick"（~30指標）または "full"（130+指標）。
        quick: True なら mode="quick" と同等（後方互換のキーワード引数）。
        full: True なら mode="full" と同等（後方互換のキーワード引数）。

    Returns:
        NaN/inf をクリーンアップ済みの特徴量 DataFrame。
        カラム名は小文字・アンダースコア区切りに正規化済み。
    """
    if ta is None:
        raise ImportError(
            "pandas-ta がインストールされていません。"
            "pip install pandas-ta でインストールしてください。"
        )

    # quick / full キーワード引数の優先
    if quick is True:
        mode = "quick"
    elif full is True:
        mode = "full"

    if len(df) < 5:
        # データが少なすぎる場合は空の DataFrame を返す
        return pd.DataFrame()

    # pandas-ta の PerformanceWarning を抑制
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        if mode == "quick":
            feat = _calc_quick(df)
        else:
            feat = _calc_full(df)

    # カラム名正規化 & クリーンアップ
    feat = _normalize_columns(feat)
    feat = _clean_dataframe(feat)

    # 完全に値が 0 だけのカラムを除去（情報量ゼロ）
    zero_cols = [c for c in feat.columns if (feat[c] == 0).all()]
    feat = feat.drop(columns=zero_cols)

    # 重複カラム除去
    feat = feat.loc[:, ~feat.columns.duplicated()]

    return feat


# ─── ユーティリティ ────────────────────────────────────────────────────────

def list_available_indicators() -> list[str]:
    """pandas-ta で利用可能な全指標名を返す。"""
    if ta is None:
        return []
    try:
        indicators = []
        for cat in ["candle", "cycles", "momentum", "overlap",
                     "performance", "statistics", "trend",
                     "volatility", "volume"]:
            cat_list = getattr(ta, f"{cat}", None)
            if cat_list and isinstance(cat_list, list):
                indicators.extend(cat_list)
        if not indicators:
            indicators = [x for x in dir(ta) if not x.startswith("_") and callable(getattr(ta, x, None))]
        return sorted(set(indicators))
    except Exception:
        return []


def get_feature_count(mode: str = "full") -> str:
    """指定モードの概算指標数を文字列で返す（UI表示用）。"""
    if mode == "quick":
        return "~30 指標（高速モード）"
    else:
        return "130+ 指標（フルモード）"

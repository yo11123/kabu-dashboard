"""
決算データ収集スクリプト

複数ソースから決算データを収集し、統合CSVに保存する。
ソース:
  1. IRBank CSV（年次P&L全上場企業）
  2. yfinance earnings_dates（EPS実績 vs 予想）
  3. Kabutan 財務ページ（四半期決算）

使い方:
    python train/collect_earnings_data.py
"""
import os
import sys
import io
import time
import warnings
import re
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from tqdm import tqdm
from lxml import html as lhtml

warnings.filterwarnings("ignore")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# IRBank キャッシュディレクトリ
IRBANK_CACHE = DATA_DIR / "irbank_cache"
IRBANK_CACHE.mkdir(exist_ok=True)

# yfinance キャッシュ
YFINANCE_CACHE = DATA_DIR / "yfinance_earnings_cache.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://irbank.net/download",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

KABUTAN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 東証銘柄リスト取得
# ═══════════════════════════════════════════════════════════════════


def load_all_tse_tickers() -> list[str]:
    """東証全銘柄のティッカーコードを取得する。"""
    urls = [
        "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            try:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str)
            except Exception:
                df = pd.read_excel(io.BytesIO(resp.content), dtype=str, engine="xlrd")

            code_col = None
            for col in df.columns:
                if "コード" in str(col) or "code" in str(col).lower():
                    code_col = col
                    break
            if code_col is None:
                code_col = df.columns[0]

            codes = df[code_col].dropna().astype(str).str.strip().str.replace(".0", "", regex=False)
            tickers = [f"{c}.T" for c in codes if c.isdigit() and len(c) == 4]
            if len(tickers) > 500:
                print(f"JPXから {len(tickers)} 銘柄を取得")
                return tickers
        except Exception as e:
            print(f"JPXリスト取得失敗: {e}")
            continue

    # フォールバック: ローカルの日経225リスト
    tickers_path = DATA_DIR / "nikkei225_tickers.txt"
    if tickers_path.exists():
        codes = []
        with open(tickers_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if parts:
                    codes.append(parts[0].strip())
        tickers = [c for c in codes if c.endswith(".T")]
        print(f"フォールバック: 日経225 ({len(tickers)} 銘柄)")
        return tickers

    return []


# ═══════════════════════════════════════════════════════════════════
# Source 1: IRBank CSV ダウンロード
# ═══════════════════════════════════════════════════════════════════


def download_irbank_csv(url: str, cache_name: str) -> pd.DataFrame | None:
    """IRBank から CSV をダウンロードしてパースする。キャッシュあり。"""
    cache_path = IRBANK_CACHE / cache_name
    # キャッシュが24時間以内なら再利用
    if cache_path.exists():
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mtime < timedelta(hours=24):
            print(f"  キャッシュ使用: {cache_name}")
            try:
                return pd.read_csv(cache_path, encoding="utf-8")
            except Exception:
                try:
                    return pd.read_csv(cache_path, encoding="shift_jis")
                except Exception:
                    pass
    try:
        print(f"  ダウンロード中: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()

        # レスポンスをキャッシュに保存
        cache_path.write_bytes(resp.content)

        # エンコーディングを検出してパース
        for enc in ["utf-8", "shift_jis", "cp932", "euc-jp"]:
            try:
                df = pd.read_csv(io.BytesIO(resp.content), encoding=enc)
                if len(df) > 0:
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        print(f"  パース失敗: {cache_name}")
        return None
    except requests.RequestException as e:
        print(f"  ダウンロード失敗: {e}")
        return None


def collect_irbank_data() -> pd.DataFrame:
    """IRBank の年次P&L + 配当データを収集し、統合する。"""
    print("\n" + "=" * 60)
    print("Source 1: IRBank CSV データ収集")
    print("=" * 60)

    all_records = []

    # 年次P&Lデータ（最新 + 過去4年）
    years = ["", "2024", "2023", "2022", "2021"]
    for year in years:
        if year:
            url = f"https://irbank.net/download/{year}/fy-profit-and-loss.csv"
            cache_name = f"fy-profit-and-loss-{year}.csv"
            label = f"年次P&L ({year})"
        else:
            url = "https://irbank.net/download/fy-profit-and-loss.csv"
            cache_name = "fy-profit-and-loss-latest.csv"
            label = "年次P&L (最新)"

        df = download_irbank_csv(url, cache_name)
        if df is None:
            print(f"  {label}: 取得失敗")
            continue

        print(f"  {label}: {len(df)} 行, カラム: {list(df.columns[:8])}")

        # カラム名の標準化（IRBankのCSVフォーマットに対応）
        # 一般的なカラム: コード, 社名, 決算期, 売上高, 営業利益, 経常利益, 純利益, EPS等
        col_map = {}
        for col in df.columns:
            col_str = str(col).strip()
            if "コード" in col_str or "code" in col_str.lower() or "銘柄" in col_str:
                col_map[col] = "code"
            elif "決算" in col_str or "期" in col_str:
                col_map[col] = "fiscal_period"
            elif "売上" in col_str or "revenue" in col_str.lower() or "sales" in col_str.lower():
                col_map[col] = "sales"
            elif "営業" in col_str and ("利益" in col_str or "益" in col_str):
                col_map[col] = "operating_profit"
            elif "経常" in col_str:
                col_map[col] = "ordinary_profit"
            elif "純" in col_str and ("利益" in col_str or "益" in col_str):
                col_map[col] = "net_profit"
            elif "eps" in col_str.lower() or "1株" in col_str:
                col_map[col] = "eps"
            elif "配当" in col_str or "dps" in col_str.lower() or "dividend" in col_str.lower():
                col_map[col] = "dps"
            elif "社名" in col_str or "name" in col_str.lower() or "会社" in col_str:
                col_map[col] = "company_name"

        if col_map:
            df_renamed = df.rename(columns=col_map)
        else:
            # カラム名が不明な場合、位置ベースで割り当て
            cols = list(df.columns)
            rename = {}
            if len(cols) >= 1:
                rename[cols[0]] = "code"
            if len(cols) >= 2:
                rename[cols[1]] = "company_name"
            if len(cols) >= 3:
                rename[cols[2]] = "fiscal_period"
            if len(cols) >= 4:
                rename[cols[3]] = "sales"
            if len(cols) >= 5:
                rename[cols[4]] = "operating_profit"
            if len(cols) >= 6:
                rename[cols[5]] = "ordinary_profit"
            if len(cols) >= 7:
                rename[cols[6]] = "net_profit"
            if len(cols) >= 8:
                rename[cols[7]] = "eps"
            df_renamed = df.rename(columns=rename)

        df_renamed["source"] = "irbank"
        df_renamed["data_year"] = year if year else "latest"
        all_records.append(df_renamed)
        time.sleep(1)  # レート制限配慮

    # 配当データ
    div_url = "https://irbank.net/download/fy-stock-dividend.csv"
    div_df = download_irbank_csv(div_url, "fy-stock-dividend.csv")
    if div_df is not None:
        print(f"  配当データ: {len(div_df)} 行")

    if not all_records:
        print("  IRBankからのデータ取得なし")
        return pd.DataFrame()

    combined = pd.concat(all_records, ignore_index=True)

    # コード列のクリーニング
    if "code" in combined.columns:
        combined["code"] = combined["code"].astype(str).str.strip().str.replace(".0", "", regex=False)
        # 4桁コードのみ保持
        combined = combined[combined["code"].str.match(r"^\d{4}$", na=False)]
    else:
        print("  警告: コード列が見つかりません")
        return pd.DataFrame()

    # 数値カラムの変換
    for col in ["sales", "operating_profit", "ordinary_profit", "net_profit", "eps", "dps"]:
        if col in combined.columns:
            combined[col] = pd.to_numeric(
                combined[col].astype(str).str.replace(",", "").str.replace("―", "").str.strip(),
                errors="coerce"
            )

    # 重複排除（同一コード+同一期のデータは最新のものを優先）
    if "fiscal_period" in combined.columns:
        combined = combined.drop_duplicates(subset=["code", "fiscal_period"], keep="first")

    print(f"\n  IRBank 統合結果: {len(combined)} 行, {combined['code'].nunique()} 社")
    return combined


# ═══════════════════════════════════════════════════════════════════
# Source 2: yfinance earnings_dates
# ═══════════════════════════════════════════════════════════════════


def collect_yfinance_earnings(tickers: list[str], max_tickers: int = 0) -> pd.DataFrame:
    """yfinance から決算日・EPS実績・予想を収集する。キャッシュ付き。"""
    print("\n" + "=" * 60)
    print("Source 2: yfinance 決算データ収集")
    print("=" * 60)

    # 既存キャッシュの読み込み
    cached = pd.DataFrame()
    cached_tickers = set()
    if YFINANCE_CACHE.exists():
        try:
            cached = pd.read_csv(YFINANCE_CACHE, parse_dates=["earnings_date"])
            cached_tickers = set(cached["ticker"].unique())
            print(f"  キャッシュ: {len(cached)} 件 ({len(cached_tickers)} 銘柄)")
        except Exception:
            cached = pd.DataFrame()

    # 未取得の銘柄のみ処理
    remaining = [t for t in tickers if t not in cached_tickers]
    if max_tickers > 0:
        remaining = remaining[:max_tickers]

    if not remaining:
        print(f"  全銘柄キャッシュ済み: {len(cached)} 件")
        return cached

    print(f"  新規取得対象: {len(remaining)} 銘柄")

    new_records = []
    errors = 0

    for ticker in tqdm(remaining, desc="yfinance決算取得"):
        try:
            t = yf.Ticker(ticker)
            earn_df = t.get_earnings_dates(limit=20)
            if earn_df is None or earn_df.empty:
                continue

            if earn_df.index.tz is not None:
                earn_df.index = earn_df.index.tz_localize(None)

            for dt, row in earn_df.iterrows():
                eps_act = row.get("Reported EPS")
                eps_est = row.get("EPS Estimate")
                surprise_pct = row.get("Surprise(%)")

                # 未来の決算日（まだ発表されてない）はスキップ
                if pd.isna(eps_act):
                    continue

                record = {
                    "ticker": ticker,
                    "code": ticker.replace(".T", ""),
                    "earnings_date": dt,
                    "reported_eps": eps_act,
                    "eps_estimate": eps_est,
                    "surprise_pct": surprise_pct,
                    "source": "yfinance",
                }
                new_records.append(record)

        except Exception:
            errors += 1
            continue

        # レート制限配慮（10銘柄ごとに短い休止）
        if len(new_records) % 100 == 0 and new_records:
            time.sleep(0.5)

    if new_records:
        new_df = pd.DataFrame(new_records)
        combined = pd.concat([cached, new_df], ignore_index=True)

        # 重複排除
        combined = combined.drop_duplicates(subset=["ticker", "earnings_date"], keep="last")

        # キャッシュに保存
        combined.to_csv(YFINANCE_CACHE, index=False, encoding="utf-8")
        print(f"  新規取得: {len(new_records)} 件 (エラー: {errors})")
        print(f"  キャッシュ更新: 合計 {len(combined)} 件")
        return combined
    else:
        print(f"  新規データなし (エラー: {errors})")
        return cached


# ═══════════════════════════════════════════════════════════════════
# Source 3: Kabutan 財務ページ
# ═══════════════════════════════════════════════════════════════════


def _parse_kabutan_number(text: str) -> float | None:
    """Kabutan の数値文字列を float に変換する。"""
    text = re.sub(r"[,，倍％%兆億円万\s\u3000\xa0]", "", text.strip())
    if not text or text == "―" or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_kabutan_financials(code4: str) -> list[dict]:
    """Kabutan の財務ページから四半期決算データを取得する。"""
    try:
        url = f"https://kabutan.jp/stock/finance?code={code4}"
        resp = requests.get(url, headers=KABUTAN_HEADERS, timeout=15)
        resp.raise_for_status()
        tree = lhtml.fromstring(resp.content)
        tables = tree.xpath("//table")

        financials = []

        # 年次財務データ（table[3]）
        if len(tables) > 3:
            rows = tables[3].xpath(".//tr")
            for row in rows[1:]:
                cells = [c.text_content().strip() for c in row.xpath(".//th|.//td")]
                if len(cells) < 7 or not cells[0].strip():
                    continue
                m = re.search(r"(\d{4}\.\d{2})", cells[0])
                if not m:
                    continue
                period = m.group(1)
                financials.append({
                    "code": code4,
                    "period": period,
                    "period_type": "annual",
                    "sales_m": _parse_kabutan_number(cells[1]) if len(cells) > 1 else None,
                    "op_profit_m": _parse_kabutan_number(cells[2]) if len(cells) > 2 else None,
                    "net_profit_m": _parse_kabutan_number(cells[4]) if len(cells) > 4 else None,
                    "eps": _parse_kabutan_number(cells[5]) if len(cells) > 5 else None,
                    "dps": _parse_kabutan_number(cells[6]) if len(cells) > 6 else None,
                    "source": "kabutan",
                })

        # 四半期財務データ（table[4] or table[5] — ページ構造による）
        for tbl_idx in [4, 5, 6]:
            if len(tables) <= tbl_idx:
                break
            rows = tables[tbl_idx].xpath(".//tr")
            # ヘッダーに「四半期」「Q」が含まれるかチェック
            hdr_text = "".join(c.text_content() for c in rows[0].xpath(".//th|.//td")) if rows else ""
            if "四半期" not in hdr_text and "Q" not in hdr_text.upper():
                continue
            for row in rows[1:]:
                cells = [c.text_content().strip() for c in row.xpath(".//th|.//td")]
                if len(cells) < 5 or not cells[0].strip():
                    continue
                m = re.search(r"(\d{4}\.\d{2})", cells[0])
                if not m:
                    continue
                period = m.group(1)
                # 四半期タイプの判定
                qt = "quarterly"
                if "1Q" in cells[0] or "Q1" in cells[0]:
                    qt = "Q1"
                elif "2Q" in cells[0] or "Q2" in cells[0] or "中間" in cells[0]:
                    qt = "Q2"
                elif "3Q" in cells[0] or "Q3" in cells[0]:
                    qt = "Q3"
                elif "4Q" in cells[0] or "Q4" in cells[0] or "通期" in cells[0]:
                    qt = "Q4"

                financials.append({
                    "code": code4,
                    "period": period,
                    "period_type": qt,
                    "sales_m": _parse_kabutan_number(cells[1]) if len(cells) > 1 else None,
                    "op_profit_m": _parse_kabutan_number(cells[2]) if len(cells) > 2 else None,
                    "net_profit_m": _parse_kabutan_number(cells[3]) if len(cells) > 3 else None,
                    "eps": _parse_kabutan_number(cells[4]) if len(cells) > 4 else None,
                    "dps": _parse_kabutan_number(cells[5]) if len(cells) > 5 else None,
                    "source": "kabutan",
                })

        return financials
    except Exception:
        return []


def collect_kabutan_data(tickers: list[str], max_tickers: int = 500) -> pd.DataFrame:
    """Kabutan から四半期・年次決算データを収集する。"""
    print("\n" + "=" * 60)
    print("Source 3: Kabutan 財務データ収集")
    print("=" * 60)

    # Kabutan キャッシュ
    kabutan_cache_path = DATA_DIR / "kabutan_financials_cache.csv"
    cached = pd.DataFrame()
    cached_codes = set()
    if kabutan_cache_path.exists():
        try:
            cached = pd.read_csv(kabutan_cache_path, dtype={"code": str})
            cached_codes = set(cached["code"].unique())
            print(f"  キャッシュ: {len(cached)} 件 ({len(cached_codes)} 銘柄)")
        except Exception:
            cached = pd.DataFrame()

    # 未取得銘柄を処理
    remaining_codes = []
    for t in tickers:
        code = t.replace(".T", "").strip().zfill(4)
        if code not in cached_codes:
            remaining_codes.append(code)
    remaining_codes = remaining_codes[:max_tickers]

    if not remaining_codes:
        print(f"  全銘柄キャッシュ済み: {len(cached)} 件")
        return cached

    print(f"  新規取得対象: {len(remaining_codes)} 銘柄")

    new_records = []
    errors = 0

    for code in tqdm(remaining_codes, desc="Kabutan取得"):
        records = fetch_kabutan_financials(code)
        if records:
            new_records.extend(records)
        else:
            errors += 1
        # Kabutan へのアクセスは控えめに
        time.sleep(1.0)

    if new_records:
        new_df = pd.DataFrame(new_records)
        combined = pd.concat([cached, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["code", "period", "period_type"], keep="last")
        combined.to_csv(kabutan_cache_path, index=False, encoding="utf-8")
        print(f"  新規取得: {len(new_records)} 件 (エラー: {errors})")
        print(f"  キャッシュ更新: 合計 {len(combined)} 件")
        return combined
    else:
        print(f"  新規データなし (エラー: {errors})")
        return cached


# ═══════════════════════════════════════════════════════════════════
# データ統合
# ═══════════════════════════════════════════════════════════════════


def merge_all_data(
    irbank_df: pd.DataFrame,
    yfinance_df: pd.DataFrame,
    kabutan_df: pd.DataFrame,
) -> pd.DataFrame:
    """3ソースのデータを統合して単一のCSVフォーマットに変換する。"""
    print("\n" + "=" * 60)
    print("データ統合")
    print("=" * 60)

    all_records = []

    # ── IRBank データの変換 ──
    if not irbank_df.empty and "code" in irbank_df.columns:
        print(f"  IRBank: {len(irbank_df)} 行処理中...")
        for _, row in irbank_df.iterrows():
            code = str(row.get("code", "")).strip()
            if not code or not code.isdigit():
                continue

            # 決算期から日付を推定（"2024.03" → 2024-05-15 を仮の発表日とする）
            fiscal = str(row.get("fiscal_period", ""))
            m = re.search(r"(\d{4})[\./](\d{2})", fiscal)
            if m:
                fy = int(m.group(1))
                fm = int(m.group(2))
                # 決算発表は通常決算期末の約45日後
                try:
                    from dateutil.relativedelta import relativedelta
                    est_date = datetime(fy, fm, 1) + relativedelta(months=1, days=15)
                except ImportError:
                    # dateutil がない場合の簡易推定
                    est_month = fm + 1 if fm < 12 else 1
                    est_year = fy if fm < 12 else fy + 1
                    est_date = datetime(est_year, est_month, 15)
            else:
                continue

            record = {
                "code": code,
                "ticker": f"{code}.T",
                "earnings_date": est_date,
                "period_type": "annual",
                "sales": row.get("sales"),
                "operating_profit": row.get("operating_profit"),
                "net_profit": row.get("net_profit"),
                "eps": row.get("eps"),
                "dps": row.get("dps"),
                "reported_eps": row.get("eps"),
                "eps_estimate": np.nan,
                "surprise_pct": np.nan,
                "source": "irbank",
            }
            all_records.append(record)

    # ── yfinance データの変換 ──
    if not yfinance_df.empty:
        print(f"  yfinance: {len(yfinance_df)} 行処理中...")
        for _, row in yfinance_df.iterrows():
            code = str(row.get("code", row.get("ticker", ""))).replace(".T", "").strip()
            ticker = row.get("ticker", f"{code}.T")

            record = {
                "code": code,
                "ticker": ticker,
                "earnings_date": row.get("earnings_date"),
                "period_type": "quarterly",
                "sales": np.nan,
                "operating_profit": np.nan,
                "net_profit": np.nan,
                "eps": row.get("reported_eps"),
                "dps": np.nan,
                "reported_eps": row.get("reported_eps"),
                "eps_estimate": row.get("eps_estimate"),
                "surprise_pct": row.get("surprise_pct"),
                "source": "yfinance",
            }
            all_records.append(record)

    # ── Kabutan データの変換 ──
    if not kabutan_df.empty:
        print(f"  Kabutan: {len(kabutan_df)} 行処理中...")
        for _, row in kabutan_df.iterrows():
            code = str(row.get("code", "")).strip()
            if not code or not code.isdigit():
                continue

            period = str(row.get("period", ""))
            m = re.search(r"(\d{4})\.(\d{2})", period)
            if not m:
                continue
            fy, fm = int(m.group(1)), int(m.group(2))
            period_type = str(row.get("period_type", "annual"))

            # 四半期の場合、発表日を調整
            if period_type in ["Q1", "Q2", "Q3"]:
                # 四半期決算は期末の約45日後
                try:
                    from dateutil.relativedelta import relativedelta
                    est_date = datetime(fy, fm, 1) + relativedelta(months=1, days=15)
                except ImportError:
                    est_month = fm + 1 if fm < 12 else 1
                    est_year = fy if fm < 12 else fy + 1
                    est_date = datetime(est_year, est_month, 15)
            else:
                try:
                    from dateutil.relativedelta import relativedelta
                    est_date = datetime(fy, fm, 1) + relativedelta(months=1, days=15)
                except ImportError:
                    est_month = fm + 1 if fm < 12 else 1
                    est_year = fy if fm < 12 else fy + 1
                    est_date = datetime(est_year, est_month, 15)

            # 単位: kabutan は百万円 → そのまま保持
            record = {
                "code": code,
                "ticker": f"{code}.T",
                "earnings_date": est_date,
                "period_type": period_type,
                "sales": row.get("sales_m"),
                "operating_profit": row.get("op_profit_m"),
                "net_profit": row.get("net_profit_m"),
                "eps": row.get("eps"),
                "dps": row.get("dps"),
                "reported_eps": row.get("eps"),
                "eps_estimate": np.nan,
                "surprise_pct": np.nan,
                "source": "kabutan",
            }
            all_records.append(record)

    if not all_records:
        print("  統合データなし")
        return pd.DataFrame()

    merged = pd.DataFrame(all_records)

    # earnings_date を datetime に変換
    merged["earnings_date"] = pd.to_datetime(merged["earnings_date"], errors="coerce")

    # 数値カラムの変換
    for col in ["sales", "operating_profit", "net_profit", "eps", "dps",
                "reported_eps", "eps_estimate", "surprise_pct"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")

    # yfinance のサプライズ情報で IRBank/Kabutan を補完
    # 同一銘柄・近い日付のレコードをマッチング
    yf_records = merged[merged["source"] == "yfinance"].copy()
    if not yf_records.empty:
        # yfinance のサプライズ情報をインデックス化
        yf_lookup = {}
        for _, r in yf_records.iterrows():
            if pd.notna(r["eps_estimate"]):
                key = (r["code"], r["earnings_date"].year if pd.notna(r["earnings_date"]) else None)
                yf_lookup[key] = {
                    "eps_estimate": r["eps_estimate"],
                    "surprise_pct": r["surprise_pct"],
                }

        # IRBank/Kabutan にサプライズ情報を補完
        for idx, row in merged.iterrows():
            if row["source"] in ["irbank", "kabutan"] and pd.isna(row["eps_estimate"]):
                key = (row["code"], row["earnings_date"].year if pd.notna(row["earnings_date"]) else None)
                if key in yf_lookup:
                    merged.at[idx, "eps_estimate"] = yf_lookup[key]["eps_estimate"]
                    if pd.isna(row["surprise_pct"]):
                        merged.at[idx, "surprise_pct"] = yf_lookup[key]["surprise_pct"]

    # サプライズ%を計算（まだない場合）
    mask_calc = merged["surprise_pct"].isna() & merged["reported_eps"].notna() & merged["eps_estimate"].notna()
    if mask_calc.any():
        est = merged.loc[mask_calc, "eps_estimate"]
        act = merged.loc[mask_calc, "reported_eps"]
        merged.loc[mask_calc, "surprise_pct"] = ((act - est) / est.abs().replace(0, np.nan)) * 100

    # YoY変化の計算
    merged = merged.sort_values(["code", "earnings_date"]).reset_index(drop=True)
    for col in ["sales", "operating_profit", "net_profit", "eps"]:
        if col in merged.columns:
            yoy_col = f"{col}_yoy"
            merged[yoy_col] = np.nan
            for code in merged["code"].unique():
                mask = merged["code"] == code
                vals = merged.loc[mask, col]
                if len(vals) >= 2:
                    # 前年同期比
                    shifted = vals.shift(1)
                    yoy = ((vals - shifted) / shifted.abs().replace(0, np.nan)) * 100
                    merged.loc[mask, yoy_col] = yoy

    # 重複排除（同一code + 同一日付 + 同一source）
    merged = merged.drop_duplicates(subset=["code", "earnings_date", "source"], keep="last")

    # 日付でソート
    merged = merged.sort_values("earnings_date").reset_index(drop=True)

    print(f"\n  統合結果: {len(merged):,} レコード")
    print(f"  ソース別: {merged['source'].value_counts().to_dict()}")

    return merged


# ═══════════════════════════════════════════════════════════════════
# メイン
# ═══════════════════════════════════════════════════════════════════


def main():
    start_time = time.time()

    print("=" * 60)
    print("決算データ収集スクリプト")
    print(f"  開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 銘柄リスト取得
    tickers = load_all_tse_tickers()
    print(f"対象銘柄数: {len(tickers)}")

    # ── Source 1: IRBank CSV（バルク、高速）──
    irbank_df = collect_irbank_data()

    # ── Source 2: yfinance earnings dates ──
    # 全銘柄は時間がかかるので、まず主要銘柄から
    # max_tickers=0 で全銘柄処理（キャッシュ済みはスキップ）
    yfinance_df = collect_yfinance_earnings(tickers, max_tickers=0)

    # ── Source 3: Kabutan ──
    # Kabutan はレート制限が厳しいので、最大500銘柄に制限
    kabutan_df = collect_kabutan_data(tickers, max_tickers=500)

    # ── データ統合 ──
    combined = merge_all_data(irbank_df, yfinance_df, kabutan_df)

    if combined.empty:
        print("\n最終的なデータが空です。ネットワーク接続を確認してください。")
        return

    # CSVに保存
    output_path = DATA_DIR / "earnings_combined.csv"
    combined.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\n保存完了: {output_path}")

    # ── 統計情報 ──
    print("\n" + "=" * 60)
    print("統計情報")
    print("=" * 60)
    print(f"  総レコード数: {len(combined):,}")
    print(f"  ユニーク企業数: {combined['code'].nunique():,}")

    if "earnings_date" in combined.columns:
        valid_dates = combined["earnings_date"].dropna()
        if not valid_dates.empty:
            print(f"  日付範囲: {valid_dates.min().strftime('%Y-%m-%d')} ～ {valid_dates.max().strftime('%Y-%m-%d')}")

    print(f"\n  ソース別レコード数:")
    for src, cnt in combined["source"].value_counts().items():
        print(f"    {src}: {cnt:,}")

    # サプライズ情報の充実度
    has_surprise = combined["surprise_pct"].notna().sum()
    has_estimate = combined["eps_estimate"].notna().sum()
    print(f"\n  EPS予想あり: {has_estimate:,} ({has_estimate/len(combined)*100:.1f}%)")
    print(f"  サプライズ%あり: {has_surprise:,} ({has_surprise/len(combined)*100:.1f}%)")

    # YoY情報
    for col in ["sales_yoy", "operating_profit_yoy", "net_profit_yoy", "eps_yoy"]:
        if col in combined.columns:
            cnt = combined[col].notna().sum()
            print(f"  {col}: {cnt:,} ({cnt/len(combined)*100:.1f}%)")

    elapsed = time.time() - start_time
    print(f"\n  処理時間: {elapsed/60:.1f} 分")


if __name__ == "__main__":
    main()

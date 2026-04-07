"""
データソース一覧ページ
アプリ全体で取得・使用しているデータの出所・更新頻度・キャッシュ設定をまとめる。
"""
import streamlit as st

from modules.styles import apply_theme

apply_theme()


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>データソース一覧</h1>",
        unsafe_allow_html=True,
    )
    st.caption("本アプリが取得・使用しているデータの出所・更新頻度・キャッシュ設定の一覧です")

    # ── 株価・市場データ ─────────────────────────────────────
    st.markdown("### 株価・市場データ")
    st.markdown(
        """
| データ | ソース | 更新頻度 | 用途 |
|--------|--------|----------|------|
| 日本株 株価 (OHLCV) | Yahoo Finance (`yfinance`) | 場中60秒 / 場外1時間 | チャート、テクニカル分析、スクリーナー |
| 東証全銘柄リスト | [JPX (東証)](https://www.jpx.co.jp/) Excel配信 | 24時間 | 銘柄選択、スクリーナー |
| 日経225構成銘柄 | ローカルファイル (`nikkei225_tickers.txt`) | 手動更新 | 銘柄フィルター |
| 米国主要指数 | Yahoo Finance | 5分 | S&P500, NASDAQ, ダウ, ラッセル2000 |
| VIX・SKEW | Yahoo Finance | 5分 | 恐怖指数、テールリスク |
| SOX (半導体指数) | Yahoo Finance | 5分 | セクター分析 |
| 為替 (USD/JPY, EUR/USD) | Yahoo Finance | 5分 | 為替影響分析 |
| 米国債利回り (2Y/5Y/10Y/30Y) | Yahoo Finance | 5分 | イールドカーブ、金利環境 |
| コモディティ (金/原油/銅) | Yahoo Finance | 5分 | 資産クラス分析 |
| 暗号通貨 (BTC/ETH/XRP/SOL) | Yahoo Finance | 5分 | リスク選好度 |
| ドルインデックス (DXY) | Yahoo Finance | 5分 | ドル強弱 |
| 先物 (ダウ/日経) | Yahoo Finance | 5分 | 夜間・週末の市場動向 |
"""
    )

    # ── マクロ経済指標 ───────────────────────────────────────
    st.markdown("### マクロ経済指標")
    st.markdown(
        """
| データ | ソース | 更新頻度 | APIキー |
|--------|--------|----------|---------|
| CPI (消費者物価指数) | [FRED](https://fred.stlouisfed.org/) (CPIAUCSL) | 6時間 | `FRED_API_KEY` |
| コアCPI | FRED (CPILFESL) | 6時間 | `FRED_API_KEY` |
| 雇用統計 (NFP) | FRED (PAYEMS) | 6時間 | `FRED_API_KEY` |
| 消費者信頼感指数 | FRED (UMCSENT) | 6時間 | `FRED_API_KEY` |
| 実質GDP成長率 | FRED (A191RL1Q225SBEA) | 6時間 | `FRED_API_KEY` |
| 景気先行指数 | FRED (USSLIND) | 6時間 | `FRED_API_KEY` |
| ハイイールドスプレッド | FRED (BAMLH0A0HYM2) | 6時間 | `FRED_API_KEY` |
| OECD消費者信頼感 | FRED (CSCICP03USM665S) | 6時間 | `FRED_API_KEY` |
| CAPE レシオ (シラーPE) | [multpl.com](https://www.multpl.com/) | 12時間 | 不要 |
| バフェット指標 | Yahoo Finance + FRED | 12時間 | `FRED_API_KEY` |
"""
    )

    # ── ファンダメンタル ─────────────────────────────────────
    st.markdown("### ファンダメンタル")
    st.markdown(
        """
| データ | ソース | 更新頻度 | 備考 |
|--------|--------|----------|------|
| PER / PBR / 配当利回り | [Kabutan](https://kabutan.jp/) スクレイピング | 1時間 | 4期分の財務データ含む |
| PER / PBR / ROE / ROA | Yahoo Finance (`yf.Ticker.info`) | 1時間 | グローバル基準 |
| 財務諸表 (売上/利益/EPS) | [J-Quants API](https://jpx-jquants.com/) | 1時間 | `JQUANTS_REFRESH_TOKEN` 必要 |
| 信用取引残高 (買残/売残) | J-Quants → Kabutan (フォールバック) | 1時間 | 貸借倍率の計算 |
"""
    )

    # ── ニュース・IR ────────────────────────────────────────
    st.markdown("### ニュース・IR")
    st.markdown(
        """
| データ | ソース | 更新頻度 | 備考 |
|--------|--------|----------|------|
| 銘柄ニュース | Google News RSS + yfinance | 1時間 | 日本語ニュース検索 |
| 市場ニュース (8カテゴリ) | Google News RSS | 10分 | 日本株/米国株/為替/地政学/商品/決算/マクロ/テックAI |
| 決算発表日 | yfinance + Kabutan + J-Quants | 1時間 | 3ソース統合 |
| 適時開示 (IR) | [TDNet](https://www.release.tdnet.info/) | 1時間 | 業績修正/配当/自社株買い/株式分割等 |
"""
    )

    # ── 経済カレンダー ──────────────────────────────────────
    st.markdown("### 経済カレンダー")
    st.markdown(
        """
| データ | ソース | 更新頻度 | 備考 |
|--------|--------|----------|------|
| 経済イベント (FOMC/BOJ等) | FairEconomy API (JSON) | 1時間 | 週間カレンダー |
| FOMC・日銀会合スケジュール | ハードコード (2026年分) | 年次 | 年8回ずつ |
| 月次経済指標 (CPI/ISM等) | ルールベース生成 | 月次 | 発表日の推定 |
"""
    )

    # ── AI・機械学習 ────────────────────────────────────────
    st.markdown("### AI・機械学習")
    st.markdown(
        """
| 機能 | プロバイダー | モデル | APIキー | 用途 |
|------|-------------|--------|---------|------|
| AI総合分析 | Claude / OpenAI / Gemini | 各社最新モデル | 各社APIキー | 銘柄の買い/売り判定 |
| ニュース要約 | Claude (Anthropic) | claude-haiku-4-5 | `ANTHROPIC_API_KEY` | ニュースのAI要約 |
| YouTube動画分析 | Google Gemini | gemini-2.5-flash | `GEMINI_API_KEY` | 動画字幕の要約・分析 |
| 日経予測 (ML) | ローカルモデル | XGBoost + LightGBM | 不要 | 翌営業日の方向予測 |
| 銘柄買い時判定 (ML) | ローカルモデル | XGBoost | 不要 | 上昇確率の推定 |
| 決算サプライズ (ML) | ローカルモデル | XGBoost | 不要 | 好決算確率の推定 |
"""
    )

    # ── YouTube動画分析 ─────────────────────────────────────
    st.markdown("### YouTube動画分析")
    st.markdown(
        """
| データ | ソース | 備考 |
|--------|--------|------|
| 動画字幕 | YouTube Transcript API | 日本語/英語の自動・手動字幕 |
| 動画メタデータ | YouTube oEmbed API | タイトル取得 |
| 字幕の要約・分析 | Google Gemini API (無料枠) | 1日1,500リクエストまで無料 |
"""
    )

    # ── データ永続化 ────────────────────────────────────────
    st.markdown("### データ永続化")
    st.markdown(
        """
| 対象 | ストレージ | 備考 |
|------|-----------|------|
| ポートフォリオ / ウォッチリスト | GitHub Gist + ローカルキャッシュ | リブートしても復元 |
| スクリーナー条件 | GitHub Gist + ローカルキャッシュ | 同上 |
| AI分析履歴 | GitHub Gist + ローカルキャッシュ | 最大30日分 |
| YouTube分析結果 | GitHub Gist + ローカルキャッシュ | 最大100件 |
| 相場観掲示板 | GitHub Gist + ローカルキャッシュ | 全投稿 |
"""
    )

    st.divider()

    # ── キャッシュ戦略 ──────────────────────────────────────
    st.markdown("### キャッシュ更新タイミング")

    st.markdown(
        """
| 更新間隔 | 対象 |
|----------|------|
| **60秒** | 場中の株価（リアルタイム更新） |
| **5分** | 市場指標（VIX/為替/金利/先物/暗号通貨） |
| **10分** | 市場ニュース |
| **1時間** | ファンダメンタル / 信用取引 / 決算情報 / IR / 経済カレンダー |
| **4時間** | スクリーナー / 買い時判定 |
| **6時間** | FRED マクロ経済指標 |
| **12時間** | CAPE / バフェット指標 / 決算カレンダー |
| **24時間** | 東証銘柄リスト / AI分析 |
"""
    )

    st.divider()

    # ── 必要なAPIキー ───────────────────────────────────────
    st.markdown("### 必要なAPIキー")

    st.markdown(
        """以下のキーを `secrets.toml` に設定すると各機能が有効になります。
全て未設定でも基本機能（チャート・テクニカル分析）は動作します。"""
    )

    keys_data = [
        ("GITHUB_TOKEN", "データ永続化", "https://github.com/settings/tokens", "gist権限のみ", "必須（データ保存に必要）"),
        ("GEMINI_API_KEY", "YouTube分析 / AI分析", "https://aistudio.google.com/apikey", "無料", "推奨"),
        ("ANTHROPIC_API_KEY", "AI分析 / ニュース要約", "https://console.anthropic.com/", "従量課金", "任意"),
        ("OPENAI_API_KEY", "AI分析", "https://platform.openai.com/api-keys", "従量課金", "任意"),
        ("FRED_API_KEY", "マクロ経済指標", "https://fred.stlouisfed.org/docs/api/api_key.html", "無料", "推奨"),
        ("JQUANTS_REFRESH_TOKEN", "財務諸表 / 信用取引", "https://jpx-jquants.com/", "無料プランあり", "任意"),
    ]

    st.markdown(
        "| キー名 | 機能 | 取得先 | 料金 | 優先度 |\n"
        "|--------|------|--------|------|--------|\n"
        + "\n".join(
            f"| `{name}` | {func} | [リンク]({url}) | {cost} | {prio} |"
            for name, func, url, cost, prio in keys_data
        )
    )

    st.divider()

    # ── データフロー図 ──────────────────────────────────────
    st.markdown("### データフロー概要")
    st.code(
        """
┌─────────────────────────────────────────────────────────────────┐
│                        外部データソース                          │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ Yahoo    │ Google   │ Kabutan  │ FRED     │ J-Quants │ TDNet    │
│ Finance  │ News RSS │ (株探)   │ (米経済) │ (JPX)    │ (適時開示)│
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit キャッシュ層                        │
│              st.cache_data (TTL: 60秒 ～ 24時間)                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  テクニカル   │  │ ファンダ     │  │   ニュース   │
│  分析モジュール│  │ メンタル     │  │   イベント   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI 分析エンジン                              │
│            Claude / OpenAI / Gemini / ローカルML                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      永続化ストレージ                            │
│               GitHub Gist ＋ ローカルファイル                     │
└─────────────────────────────────────────────────────────────────┘
""",
        language=None,
    )


main()

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
    st.markdown(
        """<div style="display:flex; flex-direction:column; gap:0; align-items:center; max-width:620px; margin:0 auto;">

  <!-- Layer 1: 外部データソース -->
  <div style="width:100%; margin-bottom:2px;">
    <div style="color:#9ca3af; font-size:0.7em; letter-spacing:0.15em; text-align:center; margin-bottom:6px;">EXTERNAL DATA SOURCES</div>
    <div style="display:flex; gap:6px; flex-wrap:wrap; justify-content:center;">
      <div style="background:#0d1f17; border:1px solid #2d7a5a; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#5ca08b; font-weight:600; font-size:0.85em;">Yahoo Finance</div>
        <div style="color:#6b7280; font-size:0.65em;">株価・指数・為替</div>
      </div>
      <div style="background:#0d1720; border:1px solid #2d5a7a; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#5a8cb0; font-weight:600; font-size:0.85em;">Google News</div>
        <div style="color:#6b7280; font-size:0.65em;">ニュースRSS</div>
      </div>
      <div style="background:#1a1520; border:1px solid #6b5aad; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#9b8ec4; font-weight:600; font-size:0.85em;">Kabutan</div>
        <div style="color:#6b7280; font-size:0.65em;">財務・決算</div>
      </div>
      <div style="background:#1f1a10; border:1px solid #8a7a3a; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#d4af37; font-weight:600; font-size:0.85em;">FRED</div>
        <div style="color:#6b7280; font-size:0.65em;">米マクロ経済</div>
      </div>
      <div style="background:#0d1720; border:1px solid #2d5a7a; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#5a8cb0; font-weight:600; font-size:0.85em;">J-Quants</div>
        <div style="color:#6b7280; font-size:0.65em;">JPX公式データ</div>
      </div>
      <div style="background:#1a1015; border:1px solid #7a3a4a; border-radius:6px; padding:8px 12px; text-align:center; flex:1; min-width:80px;">
        <div style="color:#c45c6c; font-weight:600; font-size:0.85em;">TDNet</div>
        <div style="color:#6b7280; font-size:0.65em;">適時開示</div>
      </div>
    </div>
  </div>

  <!-- Arrow -->
  <div style="color:#4a5568; font-size:1.5em; line-height:1; margin:4px 0;">▼</div>

  <!-- Layer 2: キャッシュ -->
  <div style="width:100%; background:linear-gradient(135deg,#111827,#0f172a); border:1px solid #374151;
              border-radius:8px; padding:12px 20px; text-align:center; margin-bottom:2px;">
    <div style="color:#6b7280; font-size:0.7em; letter-spacing:0.15em; margin-bottom:2px;">CACHE LAYER</div>
    <div style="color:#e8ecf1; font-weight:500;">Streamlit キャッシュ</div>
    <div style="color:#9ca3af; font-size:0.75em;">TTL: 60秒（リアルタイム株価）〜 24時間（銘柄リスト）</div>
  </div>

  <!-- Arrow -->
  <div style="color:#4a5568; font-size:1.5em; line-height:1; margin:4px 0;">▼</div>

  <!-- Layer 3: 分析モジュール -->
  <div style="width:100%; margin-bottom:2px;">
    <div style="color:#9ca3af; font-size:0.7em; letter-spacing:0.15em; text-align:center; margin-bottom:6px;">ANALYSIS MODULES</div>
    <div style="display:flex; gap:8px; justify-content:center;">
      <div style="background:#0d1f17; border:1px solid #2d7a5a; border-radius:6px; padding:10px 16px; text-align:center; flex:1;">
        <div style="color:#5ca08b; font-weight:600; font-size:0.9em;">テクニカル</div>
        <div style="color:#6b7280; font-size:0.7em;">RSI / MACD / 一目均衡表</div>
      </div>
      <div style="background:#1a1520; border:1px solid #6b5aad; border-radius:6px; padding:10px 16px; text-align:center; flex:1;">
        <div style="color:#9b8ec4; font-weight:600; font-size:0.9em;">ファンダメンタル</div>
        <div style="color:#6b7280; font-size:0.7em;">PER / PBR / 財務諸表</div>
      </div>
      <div style="background:#0d1720; border:1px solid #2d5a7a; border-radius:6px; padding:10px 16px; text-align:center; flex:1;">
        <div style="color:#5a8cb0; font-weight:600; font-size:0.9em;">ニュース</div>
        <div style="color:#6b7280; font-size:0.7em;">センチメント / IR</div>
      </div>
    </div>
  </div>

  <!-- Arrow -->
  <div style="color:#4a5568; font-size:1.5em; line-height:1; margin:4px 0;">▼</div>

  <!-- Layer 4: AI -->
  <div style="width:100%; background:linear-gradient(135deg,#1a1520,#13101f); border:1px solid #6b5aad;
              border-radius:8px; padding:12px 20px; text-align:center; margin-bottom:2px;">
    <div style="color:#6b7280; font-size:0.7em; letter-spacing:0.15em; margin-bottom:2px;">AI ENGINE</div>
    <div style="color:#e8ecf1; font-weight:500;">AI 分析エンジン</div>
    <div style="display:flex; gap:12px; justify-content:center; margin-top:6px;">
      <span style="color:#9b8ec4; font-size:0.8em; background:#1a1530; padding:2px 10px; border-radius:10px;">Claude</span>
      <span style="color:#5ca08b; font-size:0.8em; background:#0d1f17; padding:2px 10px; border-radius:10px;">Gemini</span>
      <span style="color:#5a8cb0; font-size:0.8em; background:#0d1720; padding:2px 10px; border-radius:10px;">OpenAI</span>
      <span style="color:#d4af37; font-size:0.8em; background:#1f1a10; padding:2px 10px; border-radius:10px;">ローカルML</span>
    </div>
  </div>

  <!-- Arrow -->
  <div style="color:#4a5568; font-size:1.5em; line-height:1; margin:4px 0;">▼</div>

  <!-- Layer 5: 永続化 -->
  <div style="width:100%; background:linear-gradient(135deg,#1f1a10,#1a1508); border:1px solid #d4af3744;
              border-radius:8px; padding:12px 20px; text-align:center;">
    <div style="color:#6b7280; font-size:0.7em; letter-spacing:0.15em; margin-bottom:2px;">PERSISTENCE</div>
    <div style="color:#e8ecf1; font-weight:500;">永続化ストレージ</div>
    <div style="color:#9ca3af; font-size:0.75em;">GitHub Gist + ローカルキャッシュ</div>
  </div>

</div>""",
        unsafe_allow_html=True,
    )


main()

"""
日経平均 翌日予測ページ

機械学習モデルによる日経平均株価の翌日方向・変動幅予測を表示する。
"""
import streamlit as st

from modules.loading import helix_spinner
from modules.styles import apply_theme

apply_theme()


def main() -> None:
    st.markdown(
        "<h1 style='font-family:Cormorant Garamond,serif; font-weight:300;"
        " letter-spacing:0.12em; font-size:1.6rem;'>日経平均 翌日予測</h1>",
        unsafe_allow_html=True,
    )
    st.caption("機械学習モデル（XGBoost + LightGBM スタッキング + Meta-Labeling）による翌営業日の方向・変動幅予測")

    from modules.ml_predictor import get_available_models

    if not get_available_models().get("日経平均翌日予測"):
        st.error("日経平均翌日予測モデルが見つかりません。`python train/train_nikkei_v2.py` で学習してください。")
        return

    # 予測実行
    with helix_spinner("日経平均の翌日予測を計算中..."):
        from modules.ml_predictor import predict_nikkei_tomorrow
        forecast = predict_nikkei_tomorrow()

    if not forecast:
        st.error("予測の計算に失敗しました。データ取得に問題がある可能性があります。")
        return

    # ── 結果表示 ──────────────────────────────────────────────
    direction = forecast["direction"]
    prob = forecast["probability"]
    base_prob = forecast.get("probability_base", prob)
    ret = forecast["expected_return"]
    exp_price = forecast["expected_price"]
    cur_price = forecast["current_price"]
    confidence = forecast["confidence"]
    news_impact = forecast.get("news_impact", "中立")
    news_hl = forecast.get("news_headline", "")
    news_sentiment = forecast.get("news_sentiment", 0)

    dir_color = "#5ca08b" if direction == "上昇" else "#c45c5c"
    dir_arrow = "▲" if direction == "上昇" else "▼"

    # メインカード
    st.markdown(
        f"""<div style="
            background: rgba(10,15,26,0.5);
            border: 1px solid {dir_color}33; border-left: 3px solid {dir_color};
            border-radius: 4px; padding: 24px 32px; margin-bottom: 20px;
        ">
            <div style="font-family:'Inter',sans-serif; font-size:0.6em; color:#6b7280;
                 text-transform:uppercase; letter-spacing:0.18em; margin-bottom:12px;">
                Nikkei 225 — Next Day Forecast (ML)
            </div>
            <div style="display:flex; align-items:baseline; gap:16px; flex-wrap:wrap;">
                <span style="font-family:'Cormorant Garamond',serif; font-size:2em; color:{dir_color}; font-weight:400;">
                    {dir_arrow} {direction}
                </span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:1.5em; color:{dir_color};">
                    {prob:.0f}%
                </span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # メトリクス
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("予想株価", f"¥{exp_price:,.0f}", f"{ret:+.2f}%",
              delta_color="normal" if ret > 0 else "inverse")
    c2.metric("現在値", f"¥{cur_price:,.0f}")
    c3.metric("確信度", confidence)
    c4.metric("ニュース影響", news_impact)

    # ニュース補正の詳細
    news_adj = round(prob - base_prob, 1)
    if abs(news_adj) >= 0.5:
        st.markdown(
            f"`ベース予測: {base_prob:.0f}%` → `ニュース補正: {news_adj:+.1f}%` → `最終予測: {prob:.0f}%`"
        )
    if news_hl:
        st.caption(f"注目ニュース: {news_hl}")

    st.divider()

    # ── 予測の説明 ────────────────────────────────────────────
    st.markdown("### この予測について")

    st.markdown(
        """**Meta-Labeling方式**による精度管理を行っています。

| 指標 | 値 |
|------|-----|
| 高信頼度時の精度 | **91.4%** |
| 高信頼度の取引回数 | 年間約174回（週3〜4回） |
| 変動幅の平均誤差 | 0.963% |

**ポイント:**
- 毎日予測は出ますが、全ての予測が高精度なわけではありません
- モデルが「この予測は自信がある」と判断した取引に限ると**精度91.4%**
- 確信度が「高い」の日 → **モデルの自信が高く精度が高い。取引を検討**
- 確信度が「五分五分」の日 → **参考程度にとどめるのが安全**
- 確信度が「高い（下落）」の日 → **リスク回避や空売りを検討**
"""
    )

    st.divider()

    # ── 使用データ・モデル構成 ─────────────────────────────────
    with st.expander("モデルの詳細"):
        st.markdown(
            """### 使用データ（リアルタイム取得）

| カテゴリ | データ |
|---------|--------|
| 日経平均 | 10年分の日次データ、テクニカル指標30+種類 |
| 米国市場 | S&P500、NASDAQ、ダウ、ラッセル2000 の前日リターン |
| センチメント | VIX（恐怖指数）の水準・変化率・レジーム |
| 為替 | ドル円の水準・1日/5日/20日リターン |
| 金利 | 米10年債/2年債利回り、イールドカーブ |
| コモディティ | 金・原油のリターン |
| 半導体 | SOX指数のリターン |
| アジア市場 | 上海総合・ハンセン指数 |
| カレンダー | 曜日、月、祝前日効果、でかんしょ節効果 |
| ニュース | リアルタイムニュースのセンチメントスコア |

### モデル構成

```
Level 0: ベースモデル
├── XGBoost（800本の決定木、GPU学習）
└── LightGBM（800本の決定木）

Level 1: スタッキング
└── Logistic Regression（メタラーナー）

Meta-Labeling: 信頼度モデル
└── XGBoost（予測が正しい確率を推定）
```

### 改善手法
- **Triple Barrier Method**: ボラティリティに応じた動的閾値でラベル生成
- **指数減衰ウェイティング**: 最新データほど重視（半減期2年）
- **カレンダーアノマリー**: 日本市場特有の季節性を考慮
- **ニュースセンチメント補正**: リアルタイムニュースで予測を補正

※あくまで統計的予測であり、投資助言ではありません。
"""
        )


main()

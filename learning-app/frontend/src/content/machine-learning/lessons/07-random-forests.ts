export const content = `
# ランダムフォレスト

## ランダムフォレストとは

ランダムフォレスト（Random Forest）は、複数の決定木を組み合わせるアンサンブル学習手法です。各決定木の予測を集約することで、単一の決定木よりも高い精度と汎化性能を実現します。

## アンサンブル学習

### バギング（Bootstrap Aggregating）

ランダムフォレストはバギングを基盤としています：

1. 元のデータからブートストラップサンプル（復元抽出）を作成
2. 各サンプルで個別の決定木を学習
3. 全ての木の予測を集約（分類: 多数決、回帰: 平均）

### ランダムな特徴量選択

各ノードの分割時に、全特徴量ではなくランダムに選んだ一部の特徴量のみを使います。これにより木同士の相関が低くなり、アンサンブルの効果が高まります。

## scikit-learn での実装

### 分類

\`\`\`python
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# データの準備
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

# ランダムフォレスト
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
\`\`\`

### 回帰

\`\`\`python
from sklearn.ensemble import RandomForestRegressor

rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
rf_reg.fit(X_train, y_train)
\`\`\`

## 特徴量の重要度

\`\`\`python
import numpy as np

importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]

for i in indices:
    print(f"{iris.feature_names[i]}: {importances[i]:.4f}")
\`\`\`

## 主要なハイパーパラメータ

- **n_estimators**: 決定木の数（多いほど安定だが計算コスト増）
- **max_depth**: 各決定木の最大深さ
- **max_features**: 各分割で考慮する特徴量の数
  - 分類: \`sqrt\`（特徴量数の平方根）がデフォルト
  - 回帰: \`1.0\`（全特徴量）がデフォルト
- **min_samples_split**: ノード分割に必要な最小サンプル数
- **min_samples_leaf**: 葉ノードに必要な最小サンプル数

## OOB（Out-of-Bag）スコア

ブートストラップで選ばれなかったデータを使って、交差検証なしで汎化性能を推定できます。

\`\`\`python
rf = RandomForestClassifier(n_estimators=100, oob_score=True, random_state=42)
rf.fit(X_train, y_train)
print(f"OOBスコア: {rf.oob_score_:.2f}")
\`\`\`

## メリットとデメリット

### メリット
- 高い予測精度
- 過学習しにくい
- 特徴量の重要度を算出可能
- 並列処理が可能

### デメリット
- 決定木単体より解釈しにくい
- メモリと計算コストが大きい
- リアルタイム予測には遅い場合がある

## まとめ

ランダムフォレストは、実用的で高性能なアルゴリズムです。多くの機械学習コンペティションで好成績を収めており、特徴量の重要度分析にも役立ちます。
`;

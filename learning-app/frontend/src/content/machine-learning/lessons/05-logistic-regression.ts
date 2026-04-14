export const content = `
# ロジスティック回帰

## ロジスティック回帰とは

ロジスティック回帰（Logistic Regression）は、名前に「回帰」とありますが、実際は**分類**アルゴリズムです。入力データがあるクラスに属する確率を予測します。

## シグモイド関数

ロジスティック回帰はシグモイド関数を使って、出力を0〜1の確率に変換します：

\`\`\`
σ(z) = 1 / (1 + e^(-z))
z = w1*x1 + w2*x2 + ... + wn*xn + b
\`\`\`

- 出力が0.5以上 → クラス1
- 出力が0.5未満 → クラス0

## 損失関数

交差エントロピー（Log Loss）を使用します：

\`\`\`
L = -1/n * Σ[yi*log(ŷi) + (1-yi)*log(1-ŷi)]
\`\`\`

## scikit-learn での実装

### 二値分類

\`\`\`python
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# データ生成
X, y = make_classification(n_samples=200, n_features=4, random_state=42)

# データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# モデルの学習
model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)

# 予測
y_pred = model.predict(X_test)

# 確率の予測
y_prob = model.predict_proba(X_test)

# 評価
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
print(classification_report(y_test, y_pred))
\`\`\`

### 多クラス分類

\`\`\`python
from sklearn.datasets import load_iris

# Irisデータセット（3クラス）
iris = load_iris()
X, y = iris.data, iris.target

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 多クラス分類
model = LogisticRegression(multi_class='multinomial', max_iter=200, random_state=42)
model.fit(X_train, y_train)
print(f"正解率: {model.score(X_test, y_test):.2f}")
\`\`\`

## ハイパーパラメータ

- **C**: 正則化の強さの逆数（小さいほど強い正則化）
- **penalty**: 正則化の種類（'l1', 'l2', 'elasticnet'）
- **max_iter**: 最大反復回数
- **solver**: 最適化アルゴリズム

## まとめ

ロジスティック回帰は分類問題の基本的なアルゴリズムです。解釈しやすく、確率を出力できるため、多くの実用的な場面で使われています。
`;

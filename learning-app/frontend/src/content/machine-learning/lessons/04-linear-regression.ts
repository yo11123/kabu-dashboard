export const content = `
# 線形回帰

## 線形回帰とは

線形回帰（Linear Regression）は、入力変数（特徴量）と出力変数（目的変数）の間の線形関係をモデル化する手法です。最もシンプルで理解しやすい機械学習アルゴリズムの一つです。

## 数学的な背景

### 単回帰

目的変数 y と説明変数 x の関係を一次式で表します：

\`\`\`
y = wx + b
\`\`\`

- w: 重み（傾き）
- b: バイアス（切片）

### 重回帰

複数の説明変数がある場合：

\`\`\`
y = w1*x1 + w2*x2 + ... + wn*xn + b
\`\`\`

## 損失関数

平均二乗誤差（MSE）を最小化します：

\`\`\`
MSE = (1/n) * Σ(yi - ŷi)²
\`\`\`

## scikit-learn での実装

\`\`\`python
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# サンプルデータ
from sklearn.datasets import make_regression
X, y = make_regression(n_samples=100, n_features=1, noise=10, random_state=42)

# データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# モデルの学習
model = LinearRegression()
model.fit(X_train, y_train)

# 予測
y_pred = model.predict(X_test)

# 評価
print(f"MSE: {mean_squared_error(y_test, y_pred):.2f}")
print(f"R²スコア: {r2_score(y_test, y_pred):.2f}")
print(f"重み: {model.coef_}")
print(f"切片: {model.intercept_:.2f}")
\`\`\`

## 正則化

### Ridge回帰（L2正則化）

\`\`\`python
from sklearn.linear_model import Ridge

ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)
\`\`\`

### Lasso回帰（L1正則化）

\`\`\`python
from sklearn.linear_model import Lasso

lasso = Lasso(alpha=1.0)
lasso.fit(X_train, y_train)
\`\`\`

## 線形回帰の前提条件

1. **線形性**: 特徴量と目的変数の関係が線形
2. **独立性**: 観測値が互いに独立
3. **等分散性**: 誤差の分散が一定
4. **正規性**: 誤差が正規分布に従う

## まとめ

線形回帰はシンプルですが強力なアルゴリズムです。正則化を加えることで過学習を防ぎ、より汎用的なモデルを構築できます。
`;

import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-04-01",
    title: "線形回帰モデルの構築と評価",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 線形回帰モデルを構築し、性能を評価してください
# 1. make_regression でサンプルデータを生成
# 2. データを訓練・テストに分割（test_size=0.2, random_state=42）
# 3. LinearRegression で学習
# 4. MSE と R²スコアを表示
# 5. モデルの重みと切片を表示

from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# データ生成
X, y = make_regression(n_samples=100, n_features=1, noise=10, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# データ生成
X, y = make_regression(n_samples=100, n_features=1, noise=10, random_state=42)

# データ分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# モデルの学習
model = LinearRegression()
model.fit(X_train, y_train)

# 予測
y_pred = model.predict(X_test)

# 評価
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MSE: {mse:.2f}")
print(f"R²スコア: {r2:.4f}")
print(f"重み: {model.coef_[0]:.4f}")
print(f"切片: {model.intercept_:.4f}")
`,
    hints: [
      "train_test_split で test_size=0.2, random_state=42 を指定します",
      "model.fit(X_train, y_train) で学習します",
      "model.coef_ で重み、model.intercept_ で切片を確認できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "R²スコア:",
      },
    ],
  },
  {
    id: "ml-04-02",
    title: "Ridge回帰とLasso回帰の比較",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# Ridge回帰とLasso回帰を比較してください
# 1. 多変量のデータを生成（n_features=10）
# 2. LinearRegression, Ridge, Lasso それぞれでモデルを学習
# 3. 各モデルのR²スコアを比較表示
# 4. 各モデルの重みのL2ノルム（np.linalg.norm）を表示

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

X, y = make_regression(n_samples=100, n_features=10, noise=20, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

X, y = make_regression(n_samples=100, n_features=10, noise=20, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = {
    'LinearRegression': LinearRegression(),
    'Ridge (alpha=1.0)': Ridge(alpha=1.0),
    'Lasso (alpha=1.0)': Lasso(alpha=1.0),
}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    norm = np.linalg.norm(model.coef_)
    print(f"{name}: R²={r2:.4f}, 重みのL2ノルム={norm:.4f}")
`,
    hints: [
      "Ridge(alpha=1.0) と Lasso(alpha=1.0) でモデルを作成します",
      "np.linalg.norm(model.coef_) で重みのL2ノルムを計算できます",
      "正則化が強いほど重みのノルムは小さくなります",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "LinearRegression:",
      },
    ],
  },
];

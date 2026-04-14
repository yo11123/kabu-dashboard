import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-10-01",
    title: "分類の評価指標を計算",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 分類モデルの各種評価指標を計算してください
# 1. make_classification で不均衡なデータを生成
# 2. LogisticRegression で学習・予測
# 3. 混同行列を表示
# 4. 正解率、適合率、再現率、F1スコアを表示
# 5. 分類レポートを表示

from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, f1_score, classification_report
)

X, y = make_classification(
    n_samples=300, n_features=5, weights=[0.7, 0.3], random_state=42
)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, f1_score, classification_report
)

X, y = make_classification(
    n_samples=300, n_features=5, weights=[0.7, 0.3], random_state=42
)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

print("=== 混同行列 ===")
cm = confusion_matrix(y_test, y_pred)
print(cm)

print(f"\\n正解率: {accuracy_score(y_test, y_pred):.2f}")
print(f"適合率: {precision_score(y_test, y_pred):.2f}")
print(f"再現率: {recall_score(y_test, y_pred):.2f}")
print(f"F1スコア: {f1_score(y_test, y_pred):.2f}")

print("\\n=== 分類レポート ===")
print(classification_report(y_test, y_pred))
`,
    hints: [
      "confusion_matrix(y_test, y_pred) で混同行列を生成します",
      "precision_score, recall_score, f1_score で各指標を計算します",
      "classification_report で全指標をまとめて表示できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "=== 混同行列 ===",
      },
    ],
  },
  {
    id: "ml-10-02",
    title: "回帰の評価指標を計算",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 回帰モデルの各種評価指標を計算してください
# 1. make_regression でデータを生成
# 2. LinearRegression で学習・予測
# 3. MSE, RMSE, MAE, R²スコアを表示

from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

X, y = make_regression(n_samples=200, n_features=3, noise=15, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

X, y = make_regression(n_samples=200, n_features=3, noise=15, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MSE:  {mse:.2f}")
print(f"RMSE: {rmse:.2f}")
print(f"MAE:  {mae:.2f}")
print(f"R²:   {r2:.4f}")
`,
    hints: [
      "mean_squared_error で MSE を計算し、np.sqrt で RMSE を求めます",
      "mean_absolute_error で MAE を計算します",
      "r2_score で R² スコアを計算します",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "MSE:",
      },
    ],
  },
];

import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-05-01",
    title: "ロジスティック回帰で二値分類",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# ロジスティック回帰で二値分類を行ってください
# 1. make_classification でデータを生成
# 2. データを訓練・テストに分割（test_size=0.2, random_state=42）
# 3. LogisticRegression で学習
# 4. 正解率と分類レポートを表示

from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

X, y = make_classification(n_samples=200, n_features=4, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

X, y = make_classification(n_samples=200, n_features=4, random_state=42)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
print("\\n分類レポート:")
print(classification_report(y_test, y_pred))
`,
    hints: [
      "LogisticRegression(random_state=42) でモデルを作成します",
      "model.fit(X_train, y_train) で学習、model.predict(X_test) で予測します",
      "classification_report で適合率・再現率・F1スコアが表示されます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "正解率:",
      },
    ],
  },
  {
    id: "ml-05-02",
    title: "Irisデータセットの多クラス分類",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# Irisデータセットでロジスティック回帰による多クラス分類を行ってください
# 1. Irisデータを読み込み、訓練・テスト分割
# 2. ロジスティック回帰で学習（max_iter=200）
# 3. 正解率を表示
# 4. テストデータの最初の5サンプルの予測確率を表示

from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

iris = load_iris()
X, y = iris.data, iris.target

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

iris = load_iris()
X, y = iris.data, iris.target

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter=200, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")

y_prob = model.predict_proba(X_test)
print("\\n最初の5サンプルの予測確率:")
for i in range(5):
    probs = ', '.join([f"{p:.3f}" for p in y_prob[i]])
    print(f"  サンプル{i+1}: [{probs}] -> 予測: {iris.target_names[y_pred[i]]}")
`,
    hints: [
      "LogisticRegression(max_iter=200, random_state=42) で多クラス分類に対応します",
      "model.predict_proba(X_test) で各クラスの確率を取得できます",
      "iris.target_names で予測クラスの名前を取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "正解率: 1.00",
      },
    ],
  },
];

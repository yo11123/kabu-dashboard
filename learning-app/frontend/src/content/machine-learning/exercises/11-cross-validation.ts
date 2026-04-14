import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-11-01",
    title: "交差検証でモデルを評価",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 交差検証でモデルの汎化性能を評価してください
# 1. Irisデータセットを使用
# 2. RandomForestClassifier(n_estimators=100, random_state=42)
# 3. 5-fold交差検証を実行
# 4. 各foldのスコアと平均スコアを表示

from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import cross_val_score

iris = load_iris()
X, y = iris.data, iris.target

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import cross_val_score

iris = load_iris()
X, y = iris.data, iris.target

model = RandomForestClassifier(n_estimators=100, random_state=42)
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')

print("=== 5-Fold 交差検証 ===")
for i, score in enumerate(scores):
    print(f"  Fold {i+1}: {score:.4f}")
print(f"\\n平均スコア: {scores.mean():.4f} (+/- {scores.std():.4f})")
`,
    hints: [
      "cross_val_score(model, X, y, cv=5) で5-fold交差検証を実行します",
      "scoring='accuracy' で正解率を指標にします",
      "scores.mean() と scores.std() で平均と標準偏差を求めます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "=== 5-Fold 交差検証 ===",
      },
    ],
  },
  {
    id: "ml-11-02",
    title: "GridSearchCVでハイパーパラメータチューニング",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# GridSearchCVでランダムフォレストの最適なハイパーパラメータを探してください
# 1. Irisデータセットを使用
# 2. パラメータグリッド:
#    - n_estimators: [50, 100]
#    - max_depth: [3, 5, None]
#    - min_samples_split: [2, 5]
# 3. 5-fold交差検証で最適なパラメータを探索
# 4. 最良パラメータとスコアを表示

from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import GridSearchCV

iris = load_iris()
X, y = iris.data, iris.target

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import GridSearchCV

iris = load_iris()
X, y = iris.data, iris.target

param_grid = {
    'n_estimators': [50, 100],
    'max_depth': [3, 5, None],
    'min_samples_split': [2, 5]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1
)
grid_search.fit(X, y)

print(f"最良パラメータ: {grid_search.best_params_}")
print(f"最良スコア: {grid_search.best_score_:.4f}")

print("\\n=== 上位3つの結果 ===")
import pandas as pd
results = pd.DataFrame(grid_search.cv_results_)
results = results.sort_values('rank_test_score')
for i in range(3):
    row = results.iloc[i]
    print(f"  {i+1}位: スコア={row['mean_test_score']:.4f}, パラメータ={row['params']}")
`,
    hints: [
      "GridSearchCV に モデル、param_grid、cv=5 を渡します",
      "grid_search.fit(X, y) で探索を実行します",
      "grid_search.best_params_ と grid_search.best_score_ で最良結果を取得します",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "最良パラメータ:",
      },
    ],
  },
];

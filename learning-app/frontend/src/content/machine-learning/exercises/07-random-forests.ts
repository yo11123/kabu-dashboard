import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-07-01",
    title: "ランダムフォレストの構築と特徴量重要度",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# ランダムフォレストで分類モデルを構築してください
# 1. Wineデータセットを使用
# 2. RandomForestClassifier(n_estimators=100, random_state=42) で学習
# 3. 正解率を表示
# 4. 上位5つの重要な特徴量を表示

from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")

print("\\n=== 特徴量の重要度 (上位5つ) ===")
importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]
for i in range(5):
    idx = indices[i]
    print(f"  {wine.feature_names[idx]}: {importances[idx]:.4f}")
`,
    hints: [
      "RandomForestClassifier(n_estimators=100, random_state=42) でモデルを作成します",
      "rf.feature_importances_ で重要度を取得し、np.argsort で降順にソートします",
      "load_wine() でWineデータセットを読み込みます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "正解率:",
      },
    ],
  },
  {
    id: "ml-07-02",
    title: "決定木とランダムフォレストの比較",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# 決定木とランダムフォレストの性能を比較してください
# 1. Wineデータセットを使用
# 2. DecisionTreeClassifier と RandomForestClassifier を比較
# 3. 各モデルの正解率を表示
# 4. ランダムフォレストのOOBスコアも表示

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 決定木
dt = DecisionTreeClassifier(random_state=42)
dt.fit(X_train, y_train)
dt_pred = dt.predict(X_test)
print(f"決定木の正解率: {accuracy_score(y_test, dt_pred):.2f}")

# ランダムフォレスト
rf = RandomForestClassifier(n_estimators=100, oob_score=True, random_state=42)
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)
print(f"ランダムフォレストの正解率: {accuracy_score(y_test, rf_pred):.2f}")
print(f"ランダムフォレストのOOBスコア: {rf.oob_score_:.2f}")
`,
    hints: [
      "DecisionTreeClassifier(random_state=42) で決定木を作成します",
      "RandomForestClassifier(n_estimators=100, oob_score=True, random_state=42) でOOBスコアも計算します",
      "OOBスコアは rf.oob_score_ で取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "決定木の正解率:",
      },
    ],
  },
];

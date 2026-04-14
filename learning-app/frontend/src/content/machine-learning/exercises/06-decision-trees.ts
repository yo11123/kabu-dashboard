import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-06-01",
    title: "決定木で分類と特徴量重要度の分析",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# 決定木分類器を構築し、特徴量の重要度を分析してください
# 1. Irisデータセットを使用
# 2. DecisionTreeClassifier(max_depth=3, random_state=42) で学習
# 3. テストデータでの正解率を表示
# 4. 特徴量の重要度を降順で表示
# 5. 決定木のルールをテキストで表示

from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

iris = load_iris()
X, y = iris.data, iris.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

iris = load_iris()
X, y = iris.data, iris.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = DecisionTreeClassifier(max_depth=3, random_state=42)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")

print("\\n=== 特徴量の重要度 ===")
importances = clf.feature_importances_
indices = np.argsort(importances)[::-1]
for i in indices:
    print(f"  {iris.feature_names[i]}: {importances[i]:.4f}")

print("\\n=== 決定木のルール ===")
tree_rules = export_text(clf, feature_names=list(iris.feature_names))
print(tree_rules)
`,
    hints: [
      "DecisionTreeClassifier(max_depth=3, random_state=42) でモデルを作成します",
      "clf.feature_importances_ で特徴量の重要度を取得できます",
      "export_text() で決定木のルールをテキスト形式で取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "正解率: 1.00",
      },
    ],
  },
];

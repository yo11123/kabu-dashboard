import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-12-01",
    title: "Pipelineの構築と使用",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# scikit-learnのPipelineを構築してください
# 1. Wineデータセットを使用
# 2. StandardScaler → SVC のパイプラインを作成
# 3. 訓練・テスト分割して学習・評価
# 4. パイプラインなし（スケーリングなし）のSVCと正解率を比較

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# パイプラインなし
svm_raw = SVC(random_state=42)
svm_raw.fit(X_train, y_train)
y_pred_raw = svm_raw.predict(X_test)
print(f"パイプラインなし（スケーリングなし）: {accuracy_score(y_test, y_pred_raw):.2f}")

# パイプラインあり
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('svm', SVC(random_state=42))
])
pipe.fit(X_train, y_train)
y_pred_pipe = pipe.predict(X_test)
print(f"パイプラインあり（スケーリングあり）: {accuracy_score(y_test, y_pred_pipe):.2f}")
`,
    hints: [
      "Pipeline([('scaler', StandardScaler()), ('svm', SVC())]) でパイプラインを作成します",
      "パイプラインは fit と predict を通常のモデルと同じように使えます",
      "SVMはスケーリングの有無で大きな性能差が出ます",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "パイプラインなし",
      },
    ],
  },
  {
    id: "ml-12-02",
    title: "PipelineとGridSearchCVの組み合わせ",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# PipelineとGridSearchCVを組み合わせてモデルを最適化してください
# 1. Wineデータセットを使用
# 2. StandardScaler → SVC のパイプラインを作成
# 3. GridSearchCVでSVCのハイパーパラメータを探索
#    - svm__C: [0.1, 1.0, 10.0]
#    - svm__kernel: ['linear', 'rbf']
# 4. 最良パラメータとスコアを表示
# 5. テストデータでの正解率を表示

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('svm', SVC(random_state=42))
])

param_grid = {
    'svm__C': [0.1, 1.0, 10.0],
    'svm__kernel': ['linear', 'rbf']
}

grid_search = GridSearchCV(pipe, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid_search.fit(X_train, y_train)

print(f"最良パラメータ: {grid_search.best_params_}")
print(f"最良交差検証スコア: {grid_search.best_score_:.4f}")

y_pred = grid_search.predict(X_test)
print(f"テストデータの正解率: {accuracy_score(y_test, y_pred):.2f}")
`,
    hints: [
      "パイプラインのパラメータは 'ステップ名__パラメータ名' の形式で指定します",
      "例: 'svm__C' はパイプライン内の 'svm' ステップの C パラメータを意味します",
      "GridSearchCVにパイプラインを渡すと、前処理も含めて適切に交差検証されます",
    ],
    testCases: [
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "最良パラメータ:",
      },
    ],
  },
];

import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "ml-08-01",
    title: "SVMで分類（スケーリング付き）",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `# SVMで分類を行ってください（前処理にスケーリングを含む）
# 1. Wineデータセットを使用
# 2. StandardScaler でスケーリング
# 3. SVC(kernel='rbf', random_state=42) で学習
# 4. スケーリングありとなしの正解率を比較

from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# スケーリングなし
svm_no_scale = SVC(kernel='rbf', random_state=42)
svm_no_scale.fit(X_train, y_train)
y_pred_no_scale = svm_no_scale.predict(X_test)
print(f"スケーリングなしの正解率: {accuracy_score(y_test, y_pred_no_scale):.2f}")

# スケーリングあり
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

svm_scaled = SVC(kernel='rbf', random_state=42)
svm_scaled.fit(X_train_scaled, y_train)
y_pred_scaled = svm_scaled.predict(X_test_scaled)
print(f"スケーリングありの正解率: {accuracy_score(y_test, y_pred_scaled):.2f}")
`,
    hints: [
      "StandardScaler() でスケーラーを作成し、fit_transform で訓練データをスケーリングします",
      "テストデータには transform のみを使います（fit_transform ではなく）",
      "SVMはスケーリングの有無で性能が大きく変わります",
    ],
    testCases: [
      {
        id: "tc1",
                description: "正しい結果が出力される",
                type: "stdout",
        expected: "スケーリングなしの正解率:",
      },
    ],
  },
  {
    id: "ml-08-02",
    title: "カーネル関数の比較",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `# 異なるカーネル関数のSVMの性能を比較してください
# 1. データをスケーリングしてから、linear, rbf, poly の3つのカーネルを比較
# 2. 各カーネルの正解率を表示

from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ここにコードを書いてください
`,
    solutionCode: `from sklearn.svm import SVC
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

wine = load_wine()
X, y = wine.data, wine.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

kernels = ['linear', 'rbf', 'poly']
for kernel in kernels:
    svm = SVC(kernel=kernel, random_state=42)
    svm.fit(X_train_scaled, y_train)
    y_pred = svm.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"カーネル={kernel}: 正解率={acc:.2f}")
`,
    hints: [
      "SVC(kernel='linear'), SVC(kernel='rbf'), SVC(kernel='poly') でカーネルを指定します",
      "ループで各カーネルを試すとコードが簡潔になります",
      "スケーリング済みのデータを使うことを忘れないでください",
    ],
    testCases: [
      {
        id: "tc2",
        description: "正しい結果が出力される",
        type: "stdout",
        expected: "カーネル=linear:",
      },
    ],
  },
];

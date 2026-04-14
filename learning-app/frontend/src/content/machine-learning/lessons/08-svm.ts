export const content = `
# サポートベクターマシン

## SVMとは

サポートベクターマシン（Support Vector Machine, SVM）は、データを分類するための最適な境界（超平面）を見つけるアルゴリズムです。マージンの最大化という考え方が特徴です。

## 基本概念

### マージンと超平面

- **超平面**: データを分割する決定境界
- **マージン**: 超平面と最も近いデータ点との距離
- **サポートベクター**: マージンの境界上にあるデータ点

SVMは**マージンを最大化**する超平面を見つけます。

### ハードマージンとソフトマージン

- **ハードマージン**: 全データを正しく分類（線形分離可能な場合のみ）
- **ソフトマージン**: 一部の誤分類を許容（パラメータCで制御）

## カーネルトリック

非線形な境界が必要な場合、カーネル関数で高次元空間に写像します。

### 主なカーネル

- **linear**: 線形カーネル（線形分離可能なデータ）
- **rbf**: RBFカーネル（ガウシアン、最もよく使われる）
- **poly**: 多項式カーネル
- **sigmoid**: シグモイドカーネル

## scikit-learn での実装

### 分類

\`\`\`python
from sklearn.svm import SVC
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

# データの準備
X, y = make_classification(n_samples=200, n_features=4, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# スケーリング（SVMには重要）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# SVMモデル
svm = SVC(kernel='rbf', C=1.0, gamma='scale', random_state=42)
svm.fit(X_train_scaled, y_train)

y_pred = svm.predict(X_test_scaled)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
\`\`\`

### 回帰

\`\`\`python
from sklearn.svm import SVR

svr = SVR(kernel='rbf', C=1.0)
svr.fit(X_train_scaled, y_train)
\`\`\`

## 主要なハイパーパラメータ

- **C**: 正則化パラメータ（大きいほど誤分類を許さない）
- **kernel**: カーネル関数の種類
- **gamma**: RBFカーネルの影響範囲（大きいほど複雑な境界）
- **degree**: 多項式カーネルの次数

## 前処理の重要性

SVMはスケーリングに敏感です。必ずStandardScalerやMinMaxScalerで前処理を行いましょう。

## メリットとデメリット

### メリット
- 高次元データに強い
- カーネルトリックで非線形データに対応
- 汎化性能が高い

### デメリット
- 大規模データには計算コストが大きい
- ハイパーパラメータの調整が必要
- 確率出力にはオプション設定が必要

## まとめ

SVMはマージン最大化による分類アルゴリズムで、特に中規模データセットで高い性能を発揮します。カーネルトリックにより非線形な問題にも対応できます。
`;

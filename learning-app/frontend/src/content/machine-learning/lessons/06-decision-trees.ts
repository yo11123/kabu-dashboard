export const content = `
# 決定木

## 決定木とは

決定木（Decision Tree）は、データの特徴量に基づいて条件分岐を繰り返し、予測を行うアルゴリズムです。人間が理解しやすいモデルとして知られています。

## 決定木の仕組み

### 分割基準

決定木はデータをどの特徴量でどの値で分割するかを決定します。主な基準：

- **ジニ不純度（Gini Impurity）**: クラスの混合度を測定
- **エントロピー（情報利得）**: 情報量の減少を測定

\`\`\`
ジニ不純度 = 1 - Σ(pi²)
エントロピー = -Σ(pi * log2(pi))
\`\`\`

## scikit-learn での実装

### 分類

\`\`\`python
from sklearn.tree import DecisionTreeClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# データの準備
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

# モデルの学習
clf = DecisionTreeClassifier(max_depth=3, random_state=42)
clf.fit(X_train, y_train)

# 予測と評価
y_pred = clf.predict(X_test)
print(f"正解率: {accuracy_score(y_test, y_pred):.2f}")
\`\`\`

### 回帰

\`\`\`python
from sklearn.tree import DecisionTreeRegressor

reg = DecisionTreeRegressor(max_depth=5, random_state=42)
reg.fit(X_train, y_train)
y_pred = reg.predict(X_test)
\`\`\`

### 決定木の可視化

\`\`\`python
from sklearn.tree import export_text

# テキストで表示
tree_rules = export_text(clf, feature_names=iris.feature_names)
print(tree_rules)
\`\`\`

## 重要なハイパーパラメータ

- **max_depth**: 木の最大深さ（過学習防止）
- **min_samples_split**: ノードを分割するのに必要な最小サンプル数
- **min_samples_leaf**: 葉ノードに必要な最小サンプル数
- **max_features**: 分割時に考慮する特徴量の数

## 特徴量の重要度

\`\`\`python
# 特徴量の重要度を確認
importances = clf.feature_importances_
for name, imp in zip(iris.feature_names, importances):
    print(f"{name}: {imp:.4f}")
\`\`\`

## メリットとデメリット

### メリット
- 解釈が容易
- 前処理がほとんど不要
- 数値・カテゴリカルデータ両方に対応

### デメリット
- 過学習しやすい
- データの小さな変動に敏感
- 最適な木を見つけるのはNP困難

## まとめ

決定木は直感的で解釈しやすいアルゴリズムです。過学習を防ぐためにハイパーパラメータの調整が重要です。次のレッスンでは、決定木を組み合わせて性能を向上させるランダムフォレストを学びます。
`;

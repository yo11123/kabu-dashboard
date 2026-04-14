export const content = `
# 交差検証

## 交差検証とは

交差検証（Cross-Validation）は、モデルの汎化性能をより正確に評価するための手法です。データを複数の部分に分割し、訓練と検証を繰り返します。

## なぜ交差検証が必要か

単純な train/test 分割では：

- 分割の仕方によって結果が変わる
- データを効率的に使えない
- 過学習の検出が不十分

## K-Fold 交差検証

データをK個の部分（fold）に分割し、K回の学習・評価を行います。

\`\`\`python
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

iris = load_iris()
X, y = iris.data, iris.target

model = RandomForestClassifier(n_estimators=100, random_state=42)

# 5-fold交差検証
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"各foldのスコア: {scores}")
print(f"平均スコア: {scores.mean():.3f} (+/- {scores.std():.3f})")
\`\`\`

## KFold クラスの使用

\`\`\`python
from sklearn.model_selection import KFold
import numpy as np

kf = KFold(n_splits=5, shuffle=True, random_state=42)

scores = []
for train_idx, val_idx in kf.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    score = model.score(X_val, y_val)
    scores.append(score)

print(f"平均スコア: {np.mean(scores):.3f}")
\`\`\`

## 層化K-Fold

クラスの割合を各foldで保持します。不均衡データで特に重要。

\`\`\`python
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy')
\`\`\`

## ハイパーパラメータチューニング

### GridSearchCV

\`\`\`python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [3, 5, 10, None],
    'min_samples_split': [2, 5, 10]
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
print(f"最良スコア: {grid_search.best_score_:.3f}")
\`\`\`

### RandomizedSearchCV

\`\`\`python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint

param_dist = {
    'n_estimators': randint(50, 300),
    'max_depth': [3, 5, 10, None],
    'min_samples_split': randint(2, 20)
}

random_search = RandomizedSearchCV(
    RandomForestClassifier(random_state=42),
    param_dist,
    n_iter=20,
    cv=5,
    scoring='accuracy',
    random_state=42
)
random_search.fit(X, y)
print(f"最良パラメータ: {random_search.best_params_}")
\`\`\`

## 注意点

- テストデータは最後の評価にのみ使用
- 交差検証は訓練データ内で行う
- データリーケージに注意（前処理はfold内で行う）

## まとめ

交差検証はモデル評価とハイパーパラメータチューニングに不可欠です。GridSearchCVやRandomizedSearchCVを使って効率的にモデルを最適化しましょう。
`;

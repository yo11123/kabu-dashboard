export const content = `
# パイプライン

## パイプラインとは

scikit-learn の Pipeline は、前処理からモデル学習までの複数のステップを一つのオブジェクトにまとめる仕組みです。コードの簡潔化、データリーケージの防止、再現性の向上に役立ちます。

## 基本的なパイプライン

\`\`\`python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# パイプラインの作成
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('svm', SVC(kernel='rbf', random_state=42))
])

# 学習（スケーリング + SVM学習を一度に）
pipe.fit(X_train, y_train)

# 予測（スケーリング + SVM予測を一度に）
y_pred = pipe.predict(X_test)
score = pipe.score(X_test, y_test)
\`\`\`

## make_pipeline

ステップ名を自動的に付けてくれる簡略版：

\`\`\`python
from sklearn.pipeline import make_pipeline

pipe = make_pipeline(
    StandardScaler(),
    SVC(kernel='rbf', random_state=42)
)
\`\`\`

## ColumnTransformer

異なる列に異なる前処理を適用する場合：

\`\`\`python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# 数値列とカテゴリ列で異なる処理
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), ['年齢', '収入']),
        ('cat', OneHotEncoder(), ['職業', '都市'])
    ]
)

# パイプラインに組み込む
pipe = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(random_state=42))
])
\`\`\`

## パイプラインと交差検証

\`\`\`python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(pipe, X, y, cv=5, scoring='accuracy')
print(f"平均スコア: {scores.mean():.3f}")
\`\`\`

## パイプラインとGridSearchCV

\`\`\`python
from sklearn.model_selection import GridSearchCV

# ステップ名__パラメータ名 でパラメータを指定
param_grid = {
    'svm__C': [0.1, 1.0, 10.0],
    'svm__gamma': ['scale', 'auto', 0.1, 0.01]
}

grid_search = GridSearchCV(pipe, param_grid, cv=5, scoring='accuracy')
grid_search.fit(X_train, y_train)

print(f"最良パラメータ: {grid_search.best_params_}")
print(f"最良スコア: {grid_search.best_score_:.3f}")
\`\`\`

## カスタムトランスフォーマー

\`\`\`python
from sklearn.base import BaseEstimator, TransformerMixin

class LogTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        import numpy as np
        return np.log1p(X)

# パイプラインで使用
pipe = make_pipeline(
    LogTransformer(),
    StandardScaler(),
    RandomForestClassifier(random_state=42)
)
\`\`\`

## パイプラインの保存と読み込み

\`\`\`python
import joblib

# 保存
joblib.dump(pipe, 'model_pipeline.pkl')

# 読み込み
loaded_pipe = joblib.load('model_pipeline.pkl')
y_pred = loaded_pipe.predict(X_new)
\`\`\`

## データリーケージの防止

パイプラインを使うことで、前処理がfoldごとに適切に行われ、テストデータの情報が訓練に漏れることを防げます。

## まとめ

パイプラインは機械学習ワークフローを整理し、再現性とメンテナンス性を高める重要なツールです。前処理、モデル、評価を一貫したフローとして管理しましょう。
`;

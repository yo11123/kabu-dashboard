export const content = `
# データ前処理

## なぜ前処理が重要か

機械学習モデルの性能は、入力データの品質に大きく依存します。現実のデータには欠損値、外れ値、異なるスケールの特徴量などが含まれるため、適切な前処理が不可欠です。

## 欠損値の処理

### 欠損値の確認

\`\`\`python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    '年齢': [25, np.nan, 35, 40, np.nan],
    '収入': [300, 450, np.nan, 600, 500],
    '職業': ['エンジニア', '医師', '教師', None, 'エンジニア']
})

# 欠損値の確認
print(df.isnull().sum())
\`\`\`

### 欠損値の補完

\`\`\`python
# 平均値で補完
df['年齢'].fillna(df['年齢'].mean(), inplace=True)

# 中央値で補完
df['収入'].fillna(df['収入'].median(), inplace=True)

# 最頻値で補完
df['職業'].fillna(df['職業'].mode()[0], inplace=True)

# scikit-learnのSimpleImputer
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='mean')
df[['年齢', '収入']] = imputer.fit_transform(df[['年齢', '収入']])
\`\`\`

## 特徴量のスケーリング

### 標準化（Standardization）

平均0、標準偏差1に変換します。

\`\`\`python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
\`\`\`

### 正規化（Min-Max Scaling）

値を0〜1の範囲に変換します。

\`\`\`python
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()
X_normalized = scaler.fit_transform(X)
\`\`\`

## カテゴリカルデータのエンコーディング

### Label Encoding

\`\`\`python
from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()
df['職業_encoded'] = le.fit_transform(df['職業'])
\`\`\`

### One-Hot Encoding

\`\`\`python
from sklearn.preprocessing import OneHotEncoder

# pandasを使う方法
df_encoded = pd.get_dummies(df, columns=['職業'])
\`\`\`

## データの分割

\`\`\`python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
\`\`\`

## まとめ

データ前処理は機械学習パイプラインの最も重要なステップの一つです。欠損値の処理、スケーリング、エンコーディングを適切に行うことで、モデルの性能を大幅に向上させることができます。
`;

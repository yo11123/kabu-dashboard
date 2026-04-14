export const content = `
# NumPyとPandas

## NumPy - 数値計算の基盤

NumPy は Python の数値計算ライブラリで、多次元配列（ndarray）を効率的に扱えます。

### 配列の作成

\`\`\`python
import numpy as np

# 配列の作成
a = np.array([1, 2, 3, 4, 5])
b = np.zeros((3, 3))        # 3x3のゼロ行列
c = np.ones((2, 4))         # 2x4の1行列
d = np.arange(0, 10, 2)     # [0, 2, 4, 6, 8]
e = np.linspace(0, 1, 5)    # 0から1まで5等分
\`\`\`

### 配列の演算

\`\`\`python
x = np.array([1, 2, 3])
y = np.array([4, 5, 6])

# 要素ごとの演算
print(x + y)   # [5, 7, 9]
print(x * y)   # [4, 10, 18]
print(x ** 2)  # [1, 4, 9]

# 統計量
print(np.mean(x))   # 平均
print(np.std(x))    # 標準偏差
print(np.max(x))    # 最大値
\`\`\`

### 行列演算

\`\`\`python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

print(np.dot(A, B))    # 行列積
print(A.T)             # 転置
print(np.linalg.inv(A)) # 逆行列
\`\`\`

## Pandas - データ分析の必須ツール

Pandas はデータ分析用のライブラリで、表形式のデータを扱う DataFrame が中心です。

### DataFrameの作成

\`\`\`python
import pandas as pd

# 辞書からDataFrameを作成
df = pd.DataFrame({
    '名前': ['田中', '佐藤', '鈴木'],
    '年齢': [25, 30, 35],
    '都市': ['東京', '大阪', '名古屋']
})
\`\`\`

### データの確認

\`\`\`python
df.head()       # 先頭5行
df.info()       # データ型と欠損値の情報
df.describe()   # 統計量の要約
df.shape        # 行数と列数
\`\`\`

### データの選択とフィルタリング

\`\`\`python
# 列の選択
df['名前']
df[['名前', '年齢']]

# 条件によるフィルタリング
df[df['年齢'] > 28]

# locとiloc
df.loc[0, '名前']      # ラベルベース
df.iloc[0, 0]           # 位置ベース
\`\`\`

### データの集計

\`\`\`python
df.groupby('都市')['年齢'].mean()
df['年齢'].value_counts()
df.sort_values('年齢', ascending=False)
\`\`\`

## まとめ

NumPy は高速な数値計算を提供し、Pandas は表形式データの操作を簡単にします。これらは機械学習のデータ準備に欠かせないツールです。
`;

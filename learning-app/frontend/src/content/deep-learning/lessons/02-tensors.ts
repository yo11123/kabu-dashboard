export const content = `
# テンソル操作

## テンソルとは

テンソルはPyTorchにおける基本的なデータ構造で、NumPyのndarrayに似ていますが、GPU上での計算や自動微分をサポートしています。

## テンソルの作成

\`\`\`python
import torch

# リストからテンソルを作成
a = torch.tensor([1, 2, 3])
print(f"1次元テンソル: {a}")

# 2次元テンソル（行列）
b = torch.tensor([[1, 2], [3, 4], [5, 6]])
print(f"2次元テンソル:\\n{b}")
print(f"形状: {b.shape}")

# 特殊なテンソル
zeros = torch.zeros(3, 4)       # 全て0
ones = torch.ones(2, 3)         # 全て1
rand = torch.rand(2, 3)         # 0〜1の一様乱数
randn = torch.randn(2, 3)      # 標準正規分布
arange = torch.arange(0, 10, 2) # 等差数列
\`\`\`

## テンソルの属性

\`\`\`python
t = torch.randn(3, 4)
print(f"形状: {t.shape}")
print(f"次元数: {t.ndim}")
print(f"要素数: {t.numel()}")
print(f"データ型: {t.dtype}")
print(f"デバイス: {t.device}")
\`\`\`

## テンソルの演算

### 要素ごとの演算

\`\`\`python
x = torch.tensor([1.0, 2.0, 3.0])
y = torch.tensor([4.0, 5.0, 6.0])

print(f"加算: {x + y}")
print(f"減算: {x - y}")
print(f"乗算: {x * y}")
print(f"除算: {x / y}")
print(f"べき乗: {x ** 2}")
\`\`\`

### 行列演算

\`\`\`python
a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
b = torch.tensor([[5.0, 6.0], [7.0, 8.0]])

# 行列積
print(f"行列積:\\n{torch.matmul(a, b)}")
print(f"行列積(@演算子):\\n{a @ b}")

# 転置
print(f"転置:\\n{a.T}")
\`\`\`

### リダクション演算

\`\`\`python
t = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

print(f"合計: {t.sum()}")
print(f"平均: {t.mean()}")
print(f"最大: {t.max()}")
print(f"最小: {t.min()}")

# 軸指定
print(f"列ごとの合計: {t.sum(dim=0)}")
print(f"行ごとの合計: {t.sum(dim=1)}")
\`\`\`

## テンソルの形状操作

\`\`\`python
t = torch.arange(12)

# reshape
reshaped = t.reshape(3, 4)
print(f"reshape(3,4):\\n{reshaped}")

# view（メモリ連続の場合のみ）
viewed = t.view(4, 3)
print(f"view(4,3):\\n{viewed}")

# unsqueeze / squeeze
t2 = torch.tensor([1, 2, 3])
print(f"unsqueeze(0): {t2.unsqueeze(0).shape}")  # (1, 3)
print(f"unsqueeze(1): {t2.unsqueeze(1).shape}")  # (3, 1)

# flatten
t3 = torch.randn(2, 3, 4)
print(f"flatten: {t3.flatten().shape}")  # (24,)
\`\`\`

## インデキシングとスライシング

\`\`\`python
t = torch.tensor([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

print(f"t[0]: {t[0]}")         # 最初の行
print(f"t[:, 1]: {t[:, 1]}")   # 2番目の列
print(f"t[0:2, 1:]: {t[0:2, 1:]}")  # スライス
print(f"t[t > 5]: {t[t > 5]}")      # 条件フィルタ
\`\`\`

## データ型の変換

\`\`\`python
t = torch.tensor([1, 2, 3])
print(f"元のデータ型: {t.dtype}")

t_float = t.float()
print(f"float変換: {t_float.dtype}")

t_double = t.double()
print(f"double変換: {t_double.dtype}")
\`\`\`

## NumPyとの連携

\`\`\`python
import numpy as np

# NumPy → Tensor
np_array = np.array([1, 2, 3])
tensor = torch.from_numpy(np_array)

# Tensor → NumPy
back_to_np = tensor.numpy()
\`\`\`

## まとめ

テンソルはPyTorchの基盤となるデータ構造です。作成・演算・形状操作・インデキシングを自在に使いこなすことが、深層学習プログラミングの第一歩です。
`;

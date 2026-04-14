export const content = `
# 自動微分

## 自動微分とは

自動微分（Autograd）は、PyTorchの中核機能の一つで、テンソルに対する演算の勾配（微分値）を自動的に計算します。これにより、ニューラルネットワークの学習に必要な逆伝播（バックプロパゲーション）を効率的に実装できます。

## requires_grad

テンソルの \`requires_grad\` 属性を \`True\` に設定すると、そのテンソルに対するすべての演算が記録され、勾配計算が可能になります。

\`\`\`python
import torch

# 勾配追跡を有効にしたテンソル
x = torch.tensor([2.0, 3.0], requires_grad=True)
print(f"x: {x}")
print(f"requires_grad: {x.requires_grad}")
\`\`\`

## 計算グラフと逆伝播

PyTorchは演算を行うたびに計算グラフを構築します。\`backward()\` を呼ぶことで、グラフを辿って勾配を計算します。

\`\`\`python
import torch

x = torch.tensor(3.0, requires_grad=True)

# y = x^2 + 2x + 1 の計算
y = x ** 2 + 2 * x + 1
print(f"y = {y}")

# 逆伝播で勾配を計算
y.backward()

# dy/dx = 2x + 2 = 8
print(f"dy/dx = {x.grad}")
\`\`\`

## 多変数の勾配

\`\`\`python
import torch

x = torch.tensor(1.0, requires_grad=True)
w = torch.tensor(2.0, requires_grad=True)
b = torch.tensor(0.5, requires_grad=True)

# y = w*x + b
y = w * x + b
y.backward()

print(f"dy/dx = {x.grad}")  # w = 2.0
print(f"dy/dw = {w.grad}")  # x = 1.0
print(f"dy/db = {b.grad}")  # 1.0
\`\`\`

## テンソルに対する勾配

スカラーでない出力の場合、\`backward()\` に勾配テンソルを渡す必要があります。

\`\`\`python
import torch

x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = x * 2 + 3

# ベクトルの場合はgradient引数が必要
y.backward(torch.ones_like(y))
print(f"勾配: {x.grad}")  # [2.0, 2.0, 2.0]
\`\`\`

## 勾配の累積と初期化

PyTorchでは勾配が累積されるため、学習ループでは勾配を初期化する必要があります。

\`\`\`python
import torch

x = torch.tensor(2.0, requires_grad=True)

# 1回目
y1 = x ** 2
y1.backward()
print(f"1回目の勾配: {x.grad}")  # 4.0

# 2回目（累積される）
y2 = x ** 3
y2.backward()
print(f"累積された勾配: {x.grad}")  # 4.0 + 12.0 = 16.0

# 勾配の初期化
x.grad.zero_()
print(f"初期化後: {x.grad}")  # 0.0
\`\`\`

## 勾配計算の制御

### no_grad

推論時など、勾配計算が不要な場合は \`torch.no_grad()\` を使用します。

\`\`\`python
import torch

x = torch.tensor(2.0, requires_grad=True)

with torch.no_grad():
    y = x * 3
    print(f"requires_grad: {y.requires_grad}")  # False
\`\`\`

### detach

計算グラフからテンソルを切り離すには \`detach()\` を使用します。

\`\`\`python
import torch

x = torch.tensor(2.0, requires_grad=True)
y = x ** 2
z = y.detach()
print(f"z requires_grad: {z.requires_grad}")  # False
\`\`\`

## 実践例：線形回帰の勾配計算

\`\`\`python
import torch

# データ
x = torch.tensor([1.0, 2.0, 3.0, 4.0])
y_true = torch.tensor([2.0, 4.0, 6.0, 8.0])

# パラメータ
w = torch.tensor(1.0, requires_grad=True)
b = torch.tensor(0.0, requires_grad=True)

# 予測
y_pred = w * x + b

# 損失（MSE）
loss = ((y_pred - y_true) ** 2).mean()
print(f"損失: {loss.item()}")

# 勾配計算
loss.backward()
print(f"dL/dw = {w.grad}")
print(f"dL/db = {b.grad}")
\`\`\`

## まとめ

自動微分は深層学習の学習プロセスを支える重要な機能です。\`requires_grad\`、\`backward()\`、\`no_grad()\` を理解することで、効率的にモデルを訓練できます。
`;

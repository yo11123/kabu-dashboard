export const content = `
# ニューラルネットワーク

## nn.Moduleとは

PyTorchの \`torch.nn.Module\` は、ニューラルネットワークの基底クラスです。すべてのニューラルネットワークモデルはこのクラスを継承して作成します。

## 基本的なモデルの定義

\`\`\`python
import torch
import torch.nn as nn

class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x

model = SimpleNet()
print(model)
\`\`\`

## nn.Linearレイヤー

全結合層（線形変換）を実装します。\`y = xW^T + b\`

\`\`\`python
import torch.nn as nn

# 入力特徴量10、出力特徴量5の全結合層
linear = nn.Linear(10, 5)
print(f"重み形状: {linear.weight.shape}")  # (5, 10)
print(f"バイアス形状: {linear.bias.shape}")  # (5,)
\`\`\`

## 活性化関数

\`\`\`python
import torch
import torch.nn as nn

x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])

relu = nn.ReLU()
print(f"ReLU: {relu(x)}")  # [0, 0, 0, 1, 2]

sigmoid = nn.Sigmoid()
print(f"Sigmoid: {sigmoid(x)}")

tanh = nn.Tanh()
print(f"Tanh: {tanh(x)}")

softmax = nn.Softmax(dim=0)
print(f"Softmax: {softmax(x)}")
\`\`\`

## nn.Sequential

層を順番に並べるだけのシンプルなモデルは \`nn.Sequential\` で定義できます。

\`\`\`python
import torch.nn as nn

model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(128, 10)
)

print(model)
\`\`\`

## パラメータの確認

\`\`\`python
import torch.nn as nn

model = nn.Sequential(
    nn.Linear(10, 64),
    nn.ReLU(),
    nn.Linear(64, 1)
)

# パラメータの一覧
for name, param in model.named_parameters():
    print(f"{name}: {param.shape}")

# パラメータ総数
total = sum(p.numel() for p in model.parameters())
print(f"パラメータ総数: {total}")
\`\`\`

## 損失関数

\`\`\`python
import torch
import torch.nn as nn

# 回帰用
mse_loss = nn.MSELoss()
pred = torch.tensor([2.5, 3.5])
target = torch.tensor([3.0, 4.0])
print(f"MSE: {mse_loss(pred, target)}")

# 分類用
ce_loss = nn.CrossEntropyLoss()
logits = torch.tensor([[2.0, 1.0, 0.1]])
label = torch.tensor([0])
print(f"CrossEntropy: {ce_loss(logits, label)}")
\`\`\`

## オプティマイザ

\`\`\`python
import torch.nn as nn
import torch.optim as optim

model = nn.Linear(10, 1)

# SGD
optimizer_sgd = optim.SGD(model.parameters(), lr=0.01)

# Adam
optimizer_adam = optim.Adam(model.parameters(), lr=0.001)

# 学習率スケジューラ
scheduler = optim.lr_scheduler.StepLR(optimizer_adam, step_size=10, gamma=0.1)
\`\`\`

## Dropoutと正則化

\`\`\`python
import torch.nn as nn

class RegularizedNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(100, 64)
        self.bn1 = nn.BatchNorm1d(64)  # バッチ正規化
        self.dropout = nn.Dropout(0.5)  # ドロップアウト
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = torch.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x
\`\`\`

## まとめ

\`nn.Module\` を継承してモデルを定義し、損失関数とオプティマイザを組み合わせることで、PyTorchでニューラルネットワークを構築する準備が整います。次のレッスンでは、実際の学習ループについて学びます。
`;

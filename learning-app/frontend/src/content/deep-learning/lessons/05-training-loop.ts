export const content = `
# 学習ループ

## 学習ループの全体像

深層学習モデルの学習は、以下のステップを繰り返すことで行われます：

1. **順伝播（Forward Pass）**: 入力データをモデルに通して予測を得る
2. **損失計算**: 予測と正解の差を計算
3. **逆伝播（Backward Pass）**: 勾配を計算
4. **パラメータ更新**: オプティマイザで重みを更新

\`\`\`python
import torch
import torch.nn as nn
import torch.optim as optim

# 基本的な学習ループ
for epoch in range(num_epochs):
    # 1. 順伝播
    outputs = model(inputs)

    # 2. 損失計算
    loss = criterion(outputs, targets)

    # 3. 勾配初期化 + 逆伝播
    optimizer.zero_grad()
    loss.backward()

    # 4. パラメータ更新
    optimizer.step()
\`\`\`

## DatasetとDataLoader

### Datasetクラス

\`\`\`python
from torch.utils.data import Dataset

class MyDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
\`\`\`

### DataLoader

\`\`\`python
from torch.utils.data import DataLoader

dataset = MyDataset(X_data, y_data)
dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=0
)

for batch_X, batch_y in dataloader:
    # ミニバッチ処理
    pass
\`\`\`

## 完全な学習ループの実装

\`\`\`python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# データの準備
X = torch.randn(1000, 10)
y = torch.randn(1000, 1)
dataset = TensorDataset(X, y)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# モデル、損失関数、オプティマイザの定義
model = nn.Sequential(
    nn.Linear(10, 64),
    nn.ReLU(),
    nn.Linear(64, 1)
)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 学習ループ
num_epochs = 100
for epoch in range(num_epochs):
    total_loss = 0
    for batch_X, batch_y in dataloader:
        # 順伝播
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)

        # 逆伝播とパラメータ更新
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    if (epoch + 1) % 20 == 0:
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {avg_loss:.4f}")
\`\`\`

## 訓練モードと評価モード

\`\`\`python
# 訓練モード（DropoutやBatchNormが有効）
model.train()

# 評価モード（DropoutやBatchNormが無効）
model.eval()

# 評価時は勾配計算を無効にする
with torch.no_grad():
    outputs = model(test_inputs)
\`\`\`

## 訓練と検証の分離

\`\`\`python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, random_split

# データ分割
dataset = TensorDataset(X, y)
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

for epoch in range(num_epochs):
    # 訓練フェーズ
    model.train()
    train_loss = 0
    for batch_X, batch_y in train_loader:
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        train_loss += loss.item()

    # 検証フェーズ
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            val_loss += loss.item()

    print(f"Epoch {epoch+1}: "
          f"Train Loss={train_loss/len(train_loader):.4f}, "
          f"Val Loss={val_loss/len(val_loader):.4f}")
\`\`\`

## モデルの保存と読み込み

\`\`\`python
# モデルの保存
torch.save(model.state_dict(), 'model.pth')

# モデルの読み込み
model = SimpleNet()
model.load_state_dict(torch.load('model.pth'))
model.eval()
\`\`\`

## まとめ

学習ループは深層学習の中心的なプロセスです。順伝播→損失計算→逆伝播→パラメータ更新のサイクルを正しく実装し、DataLoaderでミニバッチ処理を行い、訓練と検証を適切に分離することが重要です。
`;

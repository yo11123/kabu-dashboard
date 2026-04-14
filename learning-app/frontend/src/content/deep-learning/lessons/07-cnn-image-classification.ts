export const content = `
# CNN画像分類

## 画像分類タスク

画像分類は、入力画像がどのカテゴリに属するかを予測するタスクです。このレッスンでは、MNISTデータセットを使ってCNNによる画像分類を実装します。

## MNISTデータセット

MNISTは手書き数字（0〜9）の画像データセットです：

- **訓練データ**: 60,000枚
- **テストデータ**: 10,000枚
- **画像サイズ**: 28×28ピクセル（グレースケール）

\`\`\`python
import torch
from torchvision import datasets, transforms

# データの前処理
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

# データセットの読み込み
train_dataset = datasets.MNIST(
    root='./data', train=True, download=True, transform=transform
)
test_dataset = datasets.MNIST(
    root='./data', train=False, download=True, transform=transform
)

print(f"訓練データ数: {len(train_dataset)}")
print(f"テストデータ数: {len(test_dataset)}")
\`\`\`

## データの前処理（transforms）

\`\`\`python
from torchvision import transforms

# 一般的な前処理パイプライン
transform_train = transforms.Compose([
    transforms.RandomHorizontalFlip(),      # ランダム水平反転
    transforms.RandomRotation(10),          # ランダム回転
    transforms.ToTensor(),                  # テンソル変換
    transforms.Normalize((0.5,), (0.5,))   # 正規化
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])
\`\`\`

## 分類用CNNモデル

\`\`\`python
import torch
import torch.nn as nn
import torch.nn.functional as F

class MNISTClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout1 = nn.Dropout2d(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))   # (32, 14, 14)
        x = self.pool(F.relu(self.conv2(x)))   # (64, 7, 7)
        x = self.dropout1(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        return x
\`\`\`

## 完全な学習パイプライン

\`\`\`python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

# DataLoader
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=1000, shuffle=False)

# モデル、損失関数、オプティマイザ
model = MNISTClassifier()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 学習
def train(model, loader, criterion, optimizer, epoch):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch_idx, (data, target) in enumerate(loader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)

    accuracy = 100. * correct / total
    avg_loss = total_loss / len(loader)
    print(f"Epoch {epoch}: Loss={avg_loss:.4f}, Accuracy={accuracy:.2f}%")

# 評価
def evaluate(model, loader):
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for data, target in loader:
            output = model(data)
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)

    accuracy = 100. * correct / total
    print(f"テスト精度: {accuracy:.2f}%")
    return accuracy
\`\`\`

## 精度向上のテクニック

### 1. 学習率スケジューリング

\`\`\`python
scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode='min', factor=0.5, patience=3
)
\`\`\`

### 2. データ拡張

\`\`\`python
transform = transforms.Compose([
    transforms.RandomAffine(degrees=15, translate=(0.1, 0.1)),
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])
\`\`\`

### 3. 早期終了（Early Stopping）

\`\`\`python
best_val_loss = float('inf')
patience = 5
counter = 0

for epoch in range(100):
    train(model, train_loader, criterion, optimizer, epoch)
    val_loss = validate(model, val_loader)

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_model.pth')
        counter = 0
    else:
        counter += 1
        if counter >= patience:
            print("早期終了")
            break
\`\`\`

## 混同行列による評価

\`\`\`python
from sklearn.metrics import confusion_matrix
import numpy as np

all_preds = []
all_targets = []

model.eval()
with torch.no_grad():
    for data, target in test_loader:
        output = model(data)
        pred = output.argmax(dim=1)
        all_preds.extend(pred.numpy())
        all_targets.extend(target.numpy())

cm = confusion_matrix(all_targets, all_preds)
print("混同行列:")
print(cm)
\`\`\`

## まとめ

CNNによる画像分類では、適切なモデル設計、データの前処理・拡張、学習率のスケジューリング、早期終了などのテクニックを組み合わせることで、高い精度を達成できます。MNISTでは99%以上の精度を目指すことが可能です。
`;

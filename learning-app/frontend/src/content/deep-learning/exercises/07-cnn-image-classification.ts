import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-07-01",
    title: "画像分類の学習と評価",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(42)

# 疑似MNISTデータ（簡略化版）
# 実際のMNISTの代わりにランダムデータを使用
train_X = torch.randn(500, 1, 14, 14)
train_y = torch.randint(0, 5, (500,))
test_X = torch.randn(100, 1, 14, 14)
test_y = torch.randint(0, 5, (100,))

train_dataset = TensorDataset(train_X, train_y)
test_dataset = TensorDataset(test_X, test_y)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=100, shuffle=False)

# 問題1: CNNモデルを定義してください
# Conv1: 1→8, kernel=3, padding=1 → ReLU → MaxPool(2)  → 7x7
# Conv2: 8→16, kernel=3, padding=1 → ReLU → MaxPool(2) → 3x3（切り捨て）
# FC: 16*3*3→32 → ReLU → 32→5

class Classifier(nn.Module):
    def __init__(self):
        super().__init__()
        # ここにコードを書く
        pass

    def forward(self, x):
        # ここにコードを書く
        pass

model = Classifier()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 問題2: 訓練関数を実装してください
def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for data, target in loader:
        # ここにコードを書く
        pass
    return total_loss / len(loader), 100.0 * correct / total

# 問題3: 評価関数を実装してください
def evaluate(model, loader):
    model.eval()
    correct = 0
    total = 0
    # ここにコードを書く
    return 100.0 * correct / total

# 学習実行
for epoch in range(10):
    loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer)

test_acc = evaluate(model, test_loader)
print(f"訓練精度: {train_acc:.1f}%")
print(f"テスト精度: {test_acc:.1f}%")
print("学習完了")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(42)

# 疑似MNISTデータ（簡略化版）
train_X = torch.randn(500, 1, 14, 14)
train_y = torch.randint(0, 5, (500,))
test_X = torch.randn(100, 1, 14, 14)
test_y = torch.randint(0, 5, (100,))

train_dataset = TensorDataset(train_X, train_y)
test_dataset = TensorDataset(test_X, test_y)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=100, shuffle=False)

# 問題1: CNNモデルを定義してください
class Classifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 8, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(8, 16, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(16 * 3 * 3, 32)
        self.fc2 = nn.Linear(32, 5)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

model = Classifier()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 問題2: 訓練関数を実装してください
def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for data, target in loader:
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)
    return total_loss / len(loader), 100.0 * correct / total

# 問題3: 評価関数を実装してください
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
    return 100.0 * correct / total

# 学習実行
for epoch in range(10):
    loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer)

test_acc = evaluate(model, test_loader)
print(f"訓練精度: {train_acc:.1f}%")
print(f"テスト精度: {test_acc:.1f}%")
print("学習完了")
`,
    hints: [
      "Classifierクラスにconv1, conv2, pool, fc1, fc2を定義します",
      "forwardでは畳み込み→ReLU→プーリングを2回繰り返した後、flattenして全結合層に通します",
      "訓練関数では optimizer.zero_grad() → model(data) → criterion() → loss.backward() → optimizer.step()",
      "評価関数では torch.no_grad() ブロック内で推論し、argmax で予測クラスを取得します",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "学習完了",
      },
    ],
  },
];

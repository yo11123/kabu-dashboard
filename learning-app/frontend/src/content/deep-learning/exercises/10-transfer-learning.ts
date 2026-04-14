import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dl-10-01",
    title: "転移学習の基本設定",
    difficulty: "medium",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn

# ResNetの代わりにシンプルな事前学習済みモデルをシミュレート
class PretrainedBackbone(nn.Module):
    """事前学習済みバックボーンのシミュレーション"""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(100, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.classifier = nn.Linear(32, 1000)  # ImageNetの1000クラス

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# 問題1: 事前学習済みモデルを読み込み、特徴抽出層のパラメータを凍結してください
model = PretrainedBackbone()

# すべてのパラメータを凍結
# ここにコードを書く

# 問題2: 分類層を5クラス分類用に置き換えてください
# ここにコードを書く

# 凍結されたパラメータと学習可能なパラメータを数える
frozen_params = sum(p.numel() for p in model.parameters() if not p.requires_grad)
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

print(f"凍結パラメータ数: {frozen_params}")
print(f"学習可能パラメータ数: {trainable_params}")

# テスト
x = torch.randn(4, 100)
output = model(x)
print(f"出力形状: {output.shape}")
`,
    solutionCode: `import torch
import torch.nn as nn

# ResNetの代わりにシンプルな事前学習済みモデルをシミュレート
class PretrainedBackbone(nn.Module):
    """事前学習済みバックボーンのシミュレーション"""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(100, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.classifier = nn.Linear(32, 1000)  # ImageNetの1000クラス

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# 問題1: 事前学習済みモデルを読み込み、特徴抽出層のパラメータを凍結してください
model = PretrainedBackbone()

# すべてのパラメータを凍結
for param in model.parameters():
    param.requires_grad = False

# 問題2: 分類層を5クラス分類用に置き換えてください
model.classifier = nn.Linear(32, 5)

# 凍結されたパラメータと学習可能なパラメータを数える
frozen_params = sum(p.numel() for p in model.parameters() if not p.requires_grad)
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

print(f"凍結パラメータ数: {frozen_params}")
print(f"学習可能パラメータ数: {trainable_params}")

# テスト
x = torch.randn(4, 100)
output = model(x)
print(f"出力形状: {output.shape}")
`,
    hints: [
      "for param in model.parameters(): param.requires_grad = False ですべてを凍結します",
      "model.classifier = nn.Linear(32, 5) で新しい分類層に置き換えます",
      "新しく作成した層のパラメータはデフォルトで requires_grad=True です",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "凍結パラメータ数: 8544",
      },
      {
        type: "stdout",
        expected: "学習可能パラメータ数: 165",
      },
      {
        type: "stdout",
        expected: "出力形状: torch.Size([4, 5])",
      },
    ],
  },
  {
    id: "dl-10-02",
    title: "転移学習による分類器の学習",
    difficulty: "hard",
    executionTarget: "backend",
    starterCode: `import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(42)

# 事前学習済みバックボーン（凍結済み）
class PretrainedBackbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(50, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
        )

    def forward(self, x):
        return self.features(x)

# 問題: 転移学習モデルを構築し、学習してください
class TransferModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = PretrainedBackbone()

        # バックボーンのパラメータを凍結
        # ここにコードを書く

        # 新しい分類ヘッドを追加（16 → 8 → num_classes）
        # ここにコードを書く

    def forward(self, x):
        # ここにコードを書く
        pass

# データ準備（3クラス分類）
X = torch.randn(300, 50)
y = torch.randint(0, 3, (300,))
dataset = TensorDataset(X, y)
loader = DataLoader(dataset, batch_size=32, shuffle=True)

# モデル・損失関数・オプティマイザ
model = TransferModel(num_classes=3)

# 学習可能なパラメータのみをオプティマイザに渡す
optimizer = optim.Adam(
    filter(lambda p: p.requires_grad, model.parameters()),
    lr=0.01
)
criterion = nn.CrossEntropyLoss()

# 学習ループ
for epoch in range(20):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for batch_X, batch_y in loader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        pred = outputs.argmax(dim=1)
        correct += pred.eq(batch_y).sum().item()
        total += batch_y.size(0)

    if (epoch + 1) % 10 == 0:
        acc = 100.0 * correct / total
        print(f"Epoch {epoch+1}: Loss={total_loss/len(loader):.4f}, Acc={acc:.1f}%")

# パラメータ情報
frozen = sum(p.numel() for p in model.parameters() if not p.requires_grad)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"凍結: {frozen}, 学習可能: {trainable}")
print("転移学習完了")
`,
    solutionCode: `import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

torch.manual_seed(42)

# 事前学習済みバックボーン（凍結済み）
class PretrainedBackbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(50, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
        )

    def forward(self, x):
        return self.features(x)

# 問題: 転移学習モデルを構築し、学習してください
class TransferModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = PretrainedBackbone()

        # バックボーンのパラメータを凍結
        for param in self.backbone.parameters():
            param.requires_grad = False

        # 新しい分類ヘッドを追加（16 → 8 → num_classes）
        self.head = nn.Sequential(
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, num_classes),
        )

    def forward(self, x):
        features = self.backbone(x)
        out = self.head(features)
        return out

# データ準備（3クラス分類）
X = torch.randn(300, 50)
y = torch.randint(0, 3, (300,))
dataset = TensorDataset(X, y)
loader = DataLoader(dataset, batch_size=32, shuffle=True)

# モデル・損失関数・オプティマイザ
model = TransferModel(num_classes=3)

# 学習可能なパラメータのみをオプティマイザに渡す
optimizer = optim.Adam(
    filter(lambda p: p.requires_grad, model.parameters()),
    lr=0.01
)
criterion = nn.CrossEntropyLoss()

# 学習ループ
for epoch in range(20):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for batch_X, batch_y in loader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        pred = outputs.argmax(dim=1)
        correct += pred.eq(batch_y).sum().item()
        total += batch_y.size(0)

    if (epoch + 1) % 10 == 0:
        acc = 100.0 * correct / total
        print(f"Epoch {epoch+1}: Loss={total_loss/len(loader):.4f}, Acc={acc:.1f}%")

# パラメータ情報
frozen = sum(p.numel() for p in model.parameters() if not p.requires_grad)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"凍結: {frozen}, 学習可能: {trainable}")
print("転移学習完了")
`,
    hints: [
      "for param in self.backbone.parameters(): param.requires_grad = False で凍結します",
      "self.head = nn.Sequential(nn.Linear(16, 8), nn.ReLU(), nn.Linear(8, num_classes)) で分類ヘッドを定義",
      "forward() ではbackboneで特徴抽出し、headで分類します",
      "filter(lambda p: p.requires_grad, model.parameters()) で学習可能なパラメータだけを取得できます",
    ],
    testCases: [
      {
        type: "stdout",
        expected: "転移学習完了",
      },
    ],
  },
];

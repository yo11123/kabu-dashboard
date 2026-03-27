"""
LSTM BB ブレイクアウト成功確率モデル。
学習 (train_lstm.ipynb) と推論 (lstm_predictor.py) で共有するクラス定義。
"""
import torch
import torch.nn as nn

SEQ_LEN = 20      # 入力する過去日数
N_FEATURES = 5    # 特徴量の数（日次リターン/出来高比/BBポジション/BW/上昇率）


class LSTMClassifier(nn.Module):
    """
    BB ブレイクアウト後に 10 営業日以内に +5% 上昇するかを予測する
    バイナリ分類 LSTM。

    入力:  (batch, SEQ_LEN, N_FEATURES)
    出力:  (batch,) の成功確率 [0, 1]
    """

    def __init__(
        self,
        input_size: int = N_FEATURES,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # 最後のタイムステップを使う
        last = out[:, -1, :]        # (batch, hidden_size)
        return self.classifier(last).squeeze(-1)   # (batch,)

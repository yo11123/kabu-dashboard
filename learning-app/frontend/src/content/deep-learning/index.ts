import type { LessonMeta } from "@/types/course";

import { exercises as exercises01 } from "./exercises/01-intro-to-dl";
import { exercises as exercises02 } from "./exercises/02-tensors";
import { exercises as exercises03 } from "./exercises/03-autograd";
import { exercises as exercises04 } from "./exercises/04-neural-network";
import { exercises as exercises05 } from "./exercises/05-training-loop";
import { exercises as exercises06 } from "./exercises/06-cnn-basics";
import { exercises as exercises07 } from "./exercises/07-cnn-image-classification";
import { exercises as exercises08 } from "./exercises/08-rnn-basics";
import { exercises as exercises09 } from "./exercises/09-lstm";
import { exercises as exercises10 } from "./exercises/10-transfer-learning";

export const deepLearningLessons: LessonMeta[] = [
  { id: "01-intro-to-dl", title: "深層学習入門", description: "深層学習の基本概念とPyTorchの導入", order: 1, exercises: exercises01 },
  { id: "02-tensors", title: "テンソル操作", description: "PyTorchテンソルの作成と操作", order: 2, exercises: exercises02 },
  { id: "03-autograd", title: "自動微分", description: "PyTorchの自動微分の仕組み", order: 3, exercises: exercises03 },
  { id: "04-neural-network", title: "ニューラルネットワーク", description: "nn.Moduleによるモデル構築", order: 4, exercises: exercises04 },
  { id: "05-training-loop", title: "学習ループ", description: "モデルの訓練プロセス全体", order: 5, exercises: exercises05 },
  { id: "06-cnn-basics", title: "CNN基礎", description: "畳み込みニューラルネットワークの基礎", order: 6, exercises: exercises06 },
  { id: "07-cnn-image-classification", title: "CNN画像分類", description: "CNNによる画像分類の実装", order: 7, exercises: exercises07 },
  { id: "08-rnn-basics", title: "RNN基礎", description: "再帰型ニューラルネットワークの基礎", order: 8, exercises: exercises08 },
  { id: "09-lstm", title: "LSTM", description: "LSTMによる系列データ処理", order: 9, exercises: exercises09 },
  { id: "10-transfer-learning", title: "転移学習", description: "学習済みモデルの活用方法", order: 10, exercises: exercises10 },
];

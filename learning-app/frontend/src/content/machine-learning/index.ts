import type { LessonMeta } from "@/types/course";

import { exercises as ex01 } from "./exercises/01-intro-to-ml";
import { exercises as ex02 } from "./exercises/02-numpy-pandas";
import { exercises as ex03 } from "./exercises/03-data-preprocessing";
import { exercises as ex04 } from "./exercises/04-linear-regression";
import { exercises as ex05 } from "./exercises/05-logistic-regression";
import { exercises as ex06 } from "./exercises/06-decision-trees";
import { exercises as ex07 } from "./exercises/07-random-forests";
import { exercises as ex08 } from "./exercises/08-svm";
import { exercises as ex09 } from "./exercises/09-clustering";
import { exercises as ex10 } from "./exercises/10-evaluation-metrics";
import { exercises as ex11 } from "./exercises/11-cross-validation";
import { exercises as ex12 } from "./exercises/12-pipeline";

export const machineLearningLessons: LessonMeta[] = [
  { id: "01-intro-to-ml", title: "機械学習入門", description: "機械学習の基本概念とscikit-learn", order: 1, exercises: ex01 },
  { id: "02-numpy-pandas", title: "NumPyとPandas", description: "数値計算とデータ操作の基礎", order: 2, exercises: ex02 },
  { id: "03-data-preprocessing", title: "データ前処理", description: "欠損値処理、スケーリング、エンコーディング", order: 3, exercises: ex03 },
  { id: "04-linear-regression", title: "線形回帰", description: "回帰分析の基礎と実装", order: 4, exercises: ex04 },
  { id: "05-logistic-regression", title: "ロジスティック回帰", description: "分類問題の基礎", order: 5, exercises: ex05 },
  { id: "06-decision-trees", title: "決定木", description: "決定木による分類と特徴量の重要度", order: 6, exercises: ex06 },
  { id: "07-random-forests", title: "ランダムフォレスト", description: "アンサンブル学習の基礎", order: 7, exercises: ex07 },
  { id: "08-svm", title: "サポートベクターマシン", description: "SVMによる分類とカーネルトリック", order: 8, exercises: ex08 },
  { id: "09-clustering", title: "クラスタリング", description: "K-Means、階層型クラスタリング", order: 9, exercises: ex09 },
  { id: "10-evaluation-metrics", title: "評価指標", description: "精度、再現率、F1、AUC-ROC", order: 10, exercises: ex10 },
  { id: "11-cross-validation", title: "交差検証", description: "K-Fold、GridSearchCV", order: 11, exercises: ex11 },
  { id: "12-pipeline", title: "パイプライン", description: "前処理から予測までのパイプライン", order: 12, exercises: ex12 },
];

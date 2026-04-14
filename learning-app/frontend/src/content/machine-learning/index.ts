import type { LessonMeta } from "@/types/course";

import { exercises as introToMlExercises } from "./exercises/01-intro-to-ml";
import { exercises as numpyPandasExercises } from "./exercises/02-numpy-pandas";
import { exercises as dataPreprocessingExercises } from "./exercises/03-data-preprocessing";
import { exercises as linearRegressionExercises } from "./exercises/04-linear-regression";
import { exercises as logisticRegressionExercises } from "./exercises/05-logistic-regression";
import { exercises as decisionTreesExercises } from "./exercises/06-decision-trees";
import { exercises as randomForestsExercises } from "./exercises/07-random-forests";
import { exercises as svmExercises } from "./exercises/08-svm";
import { exercises as clusteringExercises } from "./exercises/09-clustering";
import { exercises as evaluationMetricsExercises } from "./exercises/10-evaluation-metrics";
import { exercises as crossValidationExercises } from "./exercises/11-cross-validation";
import { exercises as pipelineExercises } from "./exercises/12-pipeline";

export const machineLearningLessons: LessonMeta[] = [
  {
    id: "01-intro-to-ml",
    title: "機械学習入門",
    contentPath: () => import("./lessons/01-intro-to-ml"),
    exercises: introToMlExercises,
  },
  {
    id: "02-numpy-pandas",
    title: "NumPyとPandas",
    contentPath: () => import("./lessons/02-numpy-pandas"),
    exercises: numpyPandasExercises,
  },
  {
    id: "03-data-preprocessing",
    title: "データ前処理",
    contentPath: () => import("./lessons/03-data-preprocessing"),
    exercises: dataPreprocessingExercises,
  },
  {
    id: "04-linear-regression",
    title: "線形回帰",
    contentPath: () => import("./lessons/04-linear-regression"),
    exercises: linearRegressionExercises,
  },
  {
    id: "05-logistic-regression",
    title: "ロジスティック回帰",
    contentPath: () => import("./lessons/05-logistic-regression"),
    exercises: logisticRegressionExercises,
  },
  {
    id: "06-decision-trees",
    title: "決定木",
    contentPath: () => import("./lessons/06-decision-trees"),
    exercises: decisionTreesExercises,
  },
  {
    id: "07-random-forests",
    title: "ランダムフォレスト",
    contentPath: () => import("./lessons/07-random-forests"),
    exercises: randomForestsExercises,
  },
  {
    id: "08-svm",
    title: "サポートベクターマシン",
    contentPath: () => import("./lessons/08-svm"),
    exercises: svmExercises,
  },
  {
    id: "09-clustering",
    title: "クラスタリング",
    contentPath: () => import("./lessons/09-clustering"),
    exercises: clusteringExercises,
  },
  {
    id: "10-evaluation-metrics",
    title: "評価指標",
    contentPath: () => import("./lessons/10-evaluation-metrics"),
    exercises: evaluationMetricsExercises,
  },
  {
    id: "11-cross-validation",
    title: "交差検証",
    contentPath: () => import("./lessons/11-cross-validation"),
    exercises: crossValidationExercises,
  },
  {
    id: "12-pipeline",
    title: "パイプライン",
    contentPath: () => import("./lessons/12-pipeline"),
    exercises: pipelineExercises,
  },
];

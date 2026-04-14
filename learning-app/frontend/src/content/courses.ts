import type { Course } from "@/types/course";

export const courses: Course[] = [
  {
    id: "python-basics",
    title: "Python基礎",
    description:
      "プログラミングの基本をPythonで学びます。変数、データ型、制御構文、関数、クラスなど。",
    icon: "Code2",
    color: "#d4af37",
    lessonCount: 15,
    prerequisites: [],
  },
  {
    id: "machine-learning",
    title: "機械学習",
    description:
      "scikit-learnを使った機械学習の基礎。データ前処理、回帰、分類、評価手法など。",
    icon: "BrainCircuit",
    color: "#8fb8a0",
    lessonCount: 12,
    prerequisites: ["python-basics"],
  },
  {
    id: "deep-learning",
    title: "深層学習",
    description:
      "PyTorchで学ぶ深層学習。ニューラルネットワーク、CNN、RNN、転移学習など。",
    icon: "Network",
    color: "#7b9ed4",
    lessonCount: 10,
    prerequisites: ["machine-learning"],
  },
  {
    id: "generative-ai",
    title: "生成AI",
    description:
      "LLMとAPI活用。プロンプトエンジニアリング、RAG、チャットボット構築など。",
    icon: "Sparkles",
    color: "#c49ed4",
    lessonCount: 10,
    prerequisites: ["python-basics"],
  },
];

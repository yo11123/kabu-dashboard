import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "mod-counter",
    title: "文字の頻度を分析しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `from collections import Counter\n\n# テキストの各単語の出現回数を数え、\n# 上位3つを "単語: 回数回" の形式で出力しましょう\ntext = "the quick brown fox jumps over the lazy dog the fox"\n\n# ここにコードを書いてください\n`,
    solutionCode: `from collections import Counter\n\ntext = "the quick brown fox jumps over the lazy dog the fox"\nwords = text.split()\ncounter = Counter(words)\n\nfor word, count in counter.most_common(3):\n    print(f"{word}: {count}回")`,
    hints: [
      "split() で単語に分割し、Counter() に渡します",
      "most_common(3) で上位3つを取得できます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "上位3単語の頻度が正しく出力される",
        type: "stdout",
        expected: "the: 3回\nfox: 2回\nquick: 1回\n",
      },
    ],
  },
];

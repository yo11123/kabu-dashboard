import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "for-sum",
    title: "合計を計算しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 1から10までの合計をfor文で計算して出力しましょう\n\ntotal = 0\n# ここにfor文を書いてください\n\nprint(total)`,
    solutionCode: `total = 0\nfor i in range(1, 11):\n    total += i\nprint(total)`,
    hints: [
      "range(1, 11) で1から10までの数値を生成できます",
      "ループ内で total += i として合計に足していきます",
      "for i in range(1, 11): で1から10まで繰り返します",
    ],
    testCases: [
      {
        id: "tc1",
        description: "合計値 55 が出力される",
        type: "stdout",
        expected: "55\n",
      },
    ],
  },
  {
    id: "list-comp",
    title: "リスト内包表記を使おう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# リスト内包表記を使って、1から20までの偶数のリストを作成し出力しましょう\n\nevens = []  # ここをリスト内包表記に書き換えてください\nprint(evens)`,
    solutionCode: `evens = [i for i in range(1, 21) if i % 2 == 0]\nprint(evens)`,
    hints: [
      "リスト内包表記: [式 for 変数 in イテラブル if 条件]",
      "偶数の判定には % (剰余演算子) を使います: i % 2 == 0",
      "[i for i in range(1, 21) if i % 2 == 0] のように書きます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "偶数のリスト [2, 4, 6, ..., 20] が出力される",
        type: "stdout",
        expected: "[2, 4, 6, 8, 10, 12, 14, 16, 18, 20]\n",
      },
    ],
  },
];

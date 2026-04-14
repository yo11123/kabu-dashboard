import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "comp-matrix",
    title: "行列の転置を内包表記で書こう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# 内包表記を使って行列を転置しましょう\n# [[1,2,3],[4,5,6],[7,8,9]] → [[1,4,7],[2,5,8],[3,6,9]]\n\nmatrix = [\n    [1, 2, 3],\n    [4, 5, 6],\n    [7, 8, 9],\n]\n\n# 内包表記で転置してください\ntransposed = []  # ここを内包表記に書き換え\n\nfor row in transposed:\n    print(row)`,
    solutionCode: `matrix = [\n    [1, 2, 3],\n    [4, 5, 6],\n    [7, 8, 9],\n]\n\ntransposed = [[row[i] for row in matrix] for i in range(len(matrix[0]))]\n\nfor row in transposed:\n    print(row)`,
    hints: [
      "転置は行と列を入れ替える操作です",
      "外側のループは列のインデックス i、内側は各行 row",
      "[[row[i] for row in matrix] for i in range(len(matrix[0]))]",
    ],
    testCases: [
      {
        id: "tc1",
        description: "転置された行列が正しく出力される",
        type: "stdout",
        expected: "[1, 4, 7]\n[2, 5, 8]\n[3, 6, 9]\n",
      },
    ],
  },
  {
    id: "comp-fizzbuzz",
    title: "FizzBuzzを内包表記で",
    difficulty: "hard",
    executionTarget: "pyodide",
    starterCode: `# リスト内包表記を使ってFizzBuzzを1行で書きましょう\n# 1〜15で、3の倍数は"Fizz"、5の倍数は"Buzz"、\n# 両方の倍数は"FizzBuzz"、それ以外は数字\n\nresult = []  # ここを内包表記に書き換え\nprint(result)`,
    solutionCode: `result = ["FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else i for i in range(1, 16)]\nprint(result)`,
    hints: [
      "条件式: A if 条件 else B を内包表記の中で使えます",
      "15の倍数を最初にチェック、次に3の倍数、5の倍数の順で判定",
      "三項演算子をネスト: X if c1 else Y if c2 else Z if c3 else W",
    ],
    testCases: [
      {
        id: "tc1",
        description: "FizzBuzzが正しく出力される",
        type: "stdout",
        expected: "[1, 2, 'Fizz', 4, 'Buzz', 'Fizz', 7, 8, 'Fizz', 'Buzz', 11, 'Fizz', 13, 14, 'FizzBuzz']\n",
      },
    ],
  },
];

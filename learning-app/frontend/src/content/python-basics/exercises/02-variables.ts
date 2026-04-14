import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "var-assign",
    title: "変数に値を代入しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 変数 x に 10、変数 y に 20 を代入し、\n# その合計を変数 total に代入して出力しましょう\n`,
    solutionCode: `x = 10\ny = 20\ntotal = x + y\nprint(total)`,
    hints: [
      "変数への代入は = を使います",
      "足し算は + 演算子を使います",
      "print(total) で結果を出力しましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "合計値 30 が出力される",
        type: "stdout",
        expected: "30\n",
      },
    ],
  },
  {
    id: "var-types",
    title: "データ型を確認しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 以下の変数のデータ型をtype()で確認して出力しましょう\na = 42\nb = 3.14\nc = "hello"\nd = True\n\n# それぞれ print(type(...)) で出力してください\n`,
    solutionCode: `a = 42\nb = 3.14\nc = "hello"\nd = True\nprint(type(a))\nprint(type(b))\nprint(type(c))\nprint(type(d))`,
    hints: [
      "type() 関数で変数の型を調べられます",
      "print(type(a)) のように書きます",
      "4つの変数すべてについて type() を出力しましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "int, float, str, bool の4つの型が出力される",
        type: "custom",
        expected: {
          checkCode:
            "import sys\noutput = sys.stdout.getvalue()\nassert \"<class 'int'>\" in output, 'int型が出力されていません'\nassert \"<class 'float'>\" in output, 'float型が出力されていません'\nassert \"<class 'str'>\" in output, 'str型が出力されていません'\nassert \"<class 'bool'>\" in output, 'bool型が出力されていません'",
        },
      },
    ],
  },
];

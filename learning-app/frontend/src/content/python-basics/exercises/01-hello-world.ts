import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "hello-print",
    title: "文字列を出力しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# "こんにちは、Python!" と出力してみましょう\n`,
    solutionCode: `print("こんにちは、Python!")`,
    hints: [
      "print() 関数を使います",
      '文字列はダブルクォーテーション " " で囲みます',
      'print("こんにちは、Python!") と書いてみましょう',
    ],
    testCases: [
      {
        id: "tc1",
        description: "「こんにちは、Python!」が出力される",
        type: "stdout",
        expected: "こんにちは、Python!\n",
      },
    ],
  },
  {
    id: "hello-name",
    title: "名前を表示しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 自分の名前を変数に代入して、"私の名前は〇〇です" と出力しましょう\nname = ""\nprint()`,
    solutionCode: `name = "太郎"\nprint(f"私の名前は{name}です")`,
    hints: [
      "name 変数に名前の文字列を代入しましょう",
      "f文字列 (f-string) を使うと変数を埋め込めます",
      'f"私の名前は{name}です" のように書きます',
    ],
    testCases: [
      {
        id: "tc1",
        description: "「私の名前は〇〇です」の形式で出力される",
        type: "custom",
        expected: {
          checkCode:
            'import sys\noutput = sys.stdout.getvalue()\nassert "私の名前は" in output and "です" in output, f"出力に「私の名前は〇〇です」が含まれていません: {output}"',
        },
      },
    ],
  },
];

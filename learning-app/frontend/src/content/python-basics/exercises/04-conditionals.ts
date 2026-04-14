import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "if-basic",
    title: "数値を判定しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 変数 score の値に応じて以下を出力する関数を作りましょう\n# 80以上: "優秀"\n# 60以上: "合格"\n# それ以外: "不合格"\n\ndef judge(score):\n    # ここにコードを書いてください\n    pass\n\nprint(judge(85))\nprint(judge(65))\nprint(judge(40))`,
    solutionCode: `def judge(score):\n    if score >= 80:\n        return "優秀"\n    elif score >= 60:\n        return "合格"\n    else:\n        return "不合格"\n\nprint(judge(85))\nprint(judge(65))\nprint(judge(40))`,
    hints: [
      "if, elif, else を使って条件分岐を書きます",
      "大きい数値の条件から順に判定しましょう",
      "score >= 80 を最初にチェックし、次に score >= 60 をチェックします",
    ],
    testCases: [
      {
        id: "tc1",
        description: "85点は「優秀」と判定される",
        type: "custom",
        expected: {
          checkCode:
            'import sys\noutput = sys.stdout.getvalue()\nlines = output.strip().split("\\n")\nassert lines[0] == "優秀", f"85点の判定が正しくありません: {lines[0]}"',
        },
      },
      {
        id: "tc2",
        description: "65点は「合格」と判定される",
        type: "custom",
        expected: {
          checkCode:
            'import sys\noutput = sys.stdout.getvalue()\nlines = output.strip().split("\\n")\nassert lines[1] == "合格", f"65点の判定が正しくありません: {lines[1]}"',
        },
      },
      {
        id: "tc3",
        description: "40点は「不合格」と判定される",
        type: "custom",
        expected: {
          checkCode:
            'import sys\noutput = sys.stdout.getvalue()\nlines = output.strip().split("\\n")\nassert lines[2] == "不合格", f"40点の判定が正しくありません: {lines[2]}"',
        },
      },
    ],
  },
];

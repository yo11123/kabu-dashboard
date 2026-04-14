import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "exc-safe-div",
    title: "安全な除算関数を作ろう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# ゼロ除算と型エラーを安全に処理する除算関数を作りましょう\n# エラー時は "エラー: 〇〇" と表示して None を返してください\n\ndef safe_divide(a, b):\n    # ここにコードを書いてください\n    pass\n\nprint(safe_divide(10, 3))\nprint(safe_divide(10, 0))\nprint(safe_divide("10", 2))`,
    solutionCode: `def safe_divide(a, b):\n    try:\n        return round(a / b, 2)\n    except ZeroDivisionError:\n        print("エラー: ゼロでは割れません")\n        return None\n    except TypeError:\n        print("エラー: 数値を指定してください")\n        return None\n\nprint(safe_divide(10, 3))\nprint(safe_divide(10, 0))\nprint(safe_divide("10", 2))`,
    hints: [
      "try-except で ZeroDivisionError と TypeError を別々にキャッチします",
      "round(a / b, 2) で小数点以下2桁に丸めましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "正常な除算と例外処理が動作する",
        type: "custom",
        expected: {
          checkCode: "import sys\noutput = sys.stdout.getvalue()\nassert '3.33' in output, '10/3の結果が正しくありません'\nassert 'エラー' in output, 'エラーメッセージが出力されていません'\nassert 'None' in output, 'エラー時にNoneが返されていません'",
        },
      },
    ],
  },
];

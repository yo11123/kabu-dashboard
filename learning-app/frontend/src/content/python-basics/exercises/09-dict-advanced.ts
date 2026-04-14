import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "dict-count",
    title: "文字の出現回数を数えよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# 文字列中の各文字の出現回数を辞書で数え、\n# 出現回数の多い順に上位3つを表示しましょう\ntext = "プログラミングプログラミング言語Python"\n\n# ここにコードを書いてください\n`,
    solutionCode: `text = "プログラミングプログラミング言語Python"\n\ncount = {}\nfor ch in text:\n    count[ch] = count.get(ch, 0) + 1\n\nsorted_items = sorted(count.items(), key=lambda x: x[1], reverse=True)\nfor ch, cnt in sorted_items[:3]:\n    print(f"{ch}: {cnt}")`,
    hints: [
      "辞書のget()メソッドでデフォルト値0を指定して数えましょう",
      "sorted() の key に lambda を使って値でソートします",
      "スライス [:3] で上位3つを取得できます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "上位3文字とその回数が出力される",
        type: "custom",
        expected: {
          checkCode: "import sys\noutput = sys.stdout.getvalue()\nlines = output.strip().split('\\n')\nassert len(lines) == 3, f'3行出力されるべきですが {len(lines)} 行です'\nassert 'グ' in lines[0] or 'ン' in lines[0] or 'ロ' in lines[0], f'最頻出文字が正しくありません'",
        },
      },
    ],
  },
];

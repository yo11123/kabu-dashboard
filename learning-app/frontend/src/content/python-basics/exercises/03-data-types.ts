import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "list-basics",
    title: "リストを操作しよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# fruitsリストに "みかん" を追加し、リストの長さを出力しましょう\nfruits = ["りんご", "バナナ", "ぶどう"]\n\n# ここにコードを書いてください\n`,
    solutionCode: `fruits = ["りんご", "バナナ", "ぶどう"]\nfruits.append("みかん")\nprint(len(fruits))`,
    hints: [
      "リストに要素を追加するには append() メソッドを使います",
      "リストの長さは len() 関数で取得できます",
      'fruits.append("みかん") で追加し、print(len(fruits)) で長さを出力します',
    ],
    testCases: [
      {
        id: "tc1",
        description: "リストの長さ 4 が出力される",
        type: "stdout",
        expected: "4\n",
      },
    ],
  },
  {
    id: "dict-basics",
    title: "辞書を作ろう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# 以下の情報を持つ辞書 person を作成し、\n# "名前: 〇〇, 年齢: 〇〇" の形式で出力しましょう\n# 名前: "田中太郎", 年齢: 25\n`,
    solutionCode: `person = {"名前": "田中太郎", "年齢": 25}\nprint(f"名前: {person['名前']}, 年齢: {person['年齢']}")`,
    hints: [
      '辞書は {"キー": 値} の形式で作成します',
      "辞書の値には dict[キー] でアクセスします",
      'person = {"名前": "田中太郎", "年齢": 25} のように作成しましょう',
    ],
    testCases: [
      {
        id: "tc1",
        description: "「名前: 田中太郎, 年齢: 25」が出力される",
        type: "stdout",
        expected: "名前: 田中太郎, 年齢: 25\n",
      },
    ],
  },
];

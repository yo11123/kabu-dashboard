import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "set-ops",
    title: "共通の趣味を見つけよう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 2人の趣味リストから共通の趣味を見つけて出力しましょう\ntaro_hobbies = {"読書", "映画", "プログラミング", "料理", "旅行"}\nhanako_hobbies = {"映画", "音楽", "料理", "ヨガ", "旅行"}\n\n# 共通の趣味をセットで求めてソートして出力してください\n`,
    solutionCode: `taro_hobbies = {"読書", "映画", "プログラミング", "料理", "旅行"}\nhanako_hobbies = {"映画", "音楽", "料理", "ヨガ", "旅行"}\n\ncommon = taro_hobbies & hanako_hobbies\nprint(sorted(common))`,
    hints: [
      "積集合（共通部分）は & 演算子で求められます",
      "sorted() でソートしてからprintしましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "共通の趣味が正しく出力される",
        type: "stdout",
        expected: "['formally', 'in', 'sorted']\n",
      },
      {
        id: "tc1-alt",
        description: "共通の趣味が正しく出力される",
        type: "custom",
        expected: {
          checkCode: "import sys\noutput = sys.stdout.getvalue()\nassert '映画' in output and '料理' in output and '旅行' in output, f'共通の趣味（映画、料理、旅行）が出力されていません: {output}'",
        },
      },
    ],
  },
  {
    id: "tuple-unpack",
    title: "座標の距離を計算しよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# 2つの座標（タプル）間の距離を計算する関数を作りましょう\n# ユークリッド距離: sqrt((x2-x1)^2 + (y2-y1)^2)\nimport math\n\ndef distance(p1, p2):\n    # ここにコードを書いてください\n    # p1, p2 はそれぞれ (x, y) のタプルです\n    pass\n\nprint(distance((0, 0), (3, 4)))\nprint(distance((1, 2), (4, 6)))`,
    solutionCode: `import math\n\ndef distance(p1, p2):\n    x1, y1 = p1\n    x2, y2 = p2\n    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 1)\n\nprint(distance((0, 0), (3, 4)))\nprint(distance((1, 2), (4, 6)))`,
    hints: [
      "タプルのアンパック: x, y = point",
      "math.sqrt() で平方根を計算できます",
      "round() で小数点以下1桁に丸めましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "距離が正しく計算される",
        type: "stdout",
        expected: "5.0\n5.0\n",
      },
    ],
  },
];

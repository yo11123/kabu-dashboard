import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "json-parse",
    title: "JSONデータを処理しよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `import json\n\n# JSON文字列を解析して、各商品の情報を表示しましょう\njson_str = '[{"name": "りんご", "price": 150, "qty": 3}, {"name": "バナナ", "price": 100, "qty": 5}, {"name": "ぶどう", "price": 300, "qty": 2}]'\n\n# JSONを解析し、各商品について "商品名: 小計円" の形式で出力\n# 最後に合計金額も出力してください\n`,
    solutionCode: `import json\n\njson_str = '[{"name": "りんご", "price": 150, "qty": 3}, {"name": "バナナ", "price": 100, "qty": 5}, {"name": "ぶどう", "price": 300, "qty": 2}]'\n\nitems = json.loads(json_str)\ntotal = 0\nfor item in items:\n    subtotal = item["price"] * item["qty"]\n    total += subtotal\n    print(f"{item['name']}: {subtotal}円")\nprint(f"合計: {total}円")`,
    hints: [
      "json.loads() でJSON文字列をPythonリストに変換できます",
      "小計 = price * qty",
      "ループで各商品を処理し、合計も同時に計算しましょう",
    ],
    testCases: [
      {
        id: "tc1",
        description: "各商品の小計と合計が正しく出力される",
        type: "stdout",
        expected: "りんご: 450円\nバナナ: 500円\nぶどう: 600円\n合計: 1550円\n",
      },
    ],
  },
];

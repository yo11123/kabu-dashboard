import type { ExerciseMeta } from "@/types/course";

export const exercises: ExerciseMeta[] = [
  {
    id: "func-basic",
    title: "BMIを計算する関数を作ろう",
    difficulty: "easy",
    executionTarget: "pyodide",
    starterCode: `# 体重(kg)と身長(m)からBMIを計算する関数を作りましょう\n# BMI = 体重 / (身長 ** 2)\n# 結果は小数点以下1桁に丸めてください\n\ndef calc_bmi(weight, height):\n    # ここにコードを書いてください\n    pass\n\nprint(calc_bmi(70, 1.75))\nprint(calc_bmi(55, 1.60))`,
    solutionCode: `def calc_bmi(weight, height):\n    return round(weight / (height ** 2), 1)\n\nprint(calc_bmi(70, 1.75))\nprint(calc_bmi(55, 1.60))`,
    hints: [
      "BMIの計算式: weight / (height ** 2)",
      "round() 関数で小数点以下の桁数を指定できます",
      "round(value, 1) で小数点以下1桁に丸められます",
    ],
    testCases: [
      {
        id: "tc1",
        description: "BMI計算結果が正しい",
        type: "stdout",
        expected: "22.9\n21.5\n",
      },
    ],
  },
  {
    id: "func-lambda",
    title: "リストをソートしよう",
    difficulty: "medium",
    executionTarget: "pyodide",
    starterCode: `# students リストを点数の降順でソートして出力しましょう\n# lambda式を使ってください\n\nstudents = [\n    {"name": "太郎", "score": 85},\n    {"name": "花子", "score": 92},\n    {"name": "次郎", "score": 78},\n    {"name": "美咲", "score": 95},\n]\n\n# ここにコードを書いてください\nsorted_students = sorted(students)\n\nfor s in sorted_students:\n    print(f"{s['name']}: {s['score']}点")`,
    solutionCode: `students = [\n    {"name": "太郎", "score": 85},\n    {"name": "花子", "score": 92},\n    {"name": "次郎", "score": 78},\n    {"name": "美咲", "score": 95},\n]\n\nsorted_students = sorted(students, key=lambda s: s["score"], reverse=True)\n\nfor s in sorted_students:\n    print(f"{s['name']}: {s['score']}点")`,
    hints: [
      "sorted() の key 引数に lambda 式を渡します",
      'key=lambda s: s["score"] で点数をキーにできます',
      "reverse=True で降順になります",
    ],
    testCases: [
      {
        id: "tc1",
        description: "点数の降順でソートされる",
        type: "stdout",
        expected: "美咲: 95点\n花子: 92点\n太郎: 85点\n次郎: 78点\n",
      },
    ],
  },
];

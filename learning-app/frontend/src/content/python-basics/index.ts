import type { LessonMeta } from "@/types/course";
import { exercises as ex01 } from "./exercises/01-hello-world";
import { exercises as ex02 } from "./exercises/02-variables";
import { exercises as ex03 } from "./exercises/03-data-types";
import { exercises as ex04 } from "./exercises/04-conditionals";
import { exercises as ex05 } from "./exercises/05-loops";

export const pythonBasicsLessons: LessonMeta[] = [
  {
    id: "01-hello-world",
    title: "はじめてのPython",
    description: "print関数を使って文字列を出力しましょう",
    order: 1,
    exercises: ex01,
  },
  {
    id: "02-variables",
    title: "変数とデータ型",
    description: "変数の宣言と基本的なデータ型を学びます",
    order: 2,
    exercises: ex02,
  },
  {
    id: "03-data-types",
    title: "リストと辞書",
    description: "リスト、タプル、辞書などのコレクション型を学びます",
    order: 3,
    exercises: ex03,
  },
  {
    id: "04-conditionals",
    title: "条件分岐",
    description: "if/elif/else を使った条件分岐を学びます",
    order: 4,
    exercises: ex04,
  },
  {
    id: "05-loops",
    title: "繰り返し処理",
    description: "for文とwhile文を使ったループ処理を学びます",
    order: 5,
    exercises: ex05,
  },
];

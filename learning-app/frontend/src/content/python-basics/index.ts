import type { LessonMeta } from "@/types/course";
import { exercises as ex01 } from "./exercises/01-hello-world";
import { exercises as ex02 } from "./exercises/02-variables";
import { exercises as ex03 } from "./exercises/03-data-types";
import { exercises as ex04 } from "./exercises/04-conditionals";
import { exercises as ex05 } from "./exercises/05-loops";
import { exercises as ex06 } from "./exercises/06-functions";
import { exercises as ex07 } from "./exercises/07-strings";
import { exercises as ex08 } from "./exercises/08-tuples-sets";
import { exercises as ex09 } from "./exercises/09-dict-advanced";
import { exercises as ex10 } from "./exercises/10-file-io";
import { exercises as ex11 } from "./exercises/11-classes";
import { exercises as ex12 } from "./exercises/12-modules";
import { exercises as ex13 } from "./exercises/13-exceptions";
import { exercises as ex14 } from "./exercises/14-comprehensions";
import { exercises as ex15 } from "./exercises/15-decorators";

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
  {
    id: "06-functions",
    title: "関数",
    description: "関数の定義、引数、戻り値、lambda式を学びます",
    order: 6,
    exercises: ex06,
  },
  {
    id: "07-strings",
    title: "文字列操作",
    description: "文字列メソッド、スライス、フォーマットを学びます",
    order: 7,
    exercises: ex07,
  },
  {
    id: "08-tuples-sets",
    title: "タプルとセット",
    description: "タプル、セット、集合演算を学びます",
    order: 8,
    exercises: ex08,
  },
  {
    id: "09-dict-advanced",
    title: "辞書の応用",
    description: "辞書内包表記、ネスト辞書、ソートを学びます",
    order: 9,
    exercises: ex09,
  },
  {
    id: "10-file-io",
    title: "ファイル入出力",
    description: "ファイル操作、CSV、JSONの処理を学びます",
    order: 10,
    exercises: ex10,
  },
  {
    id: "11-classes",
    title: "クラスとオブジェクト",
    description: "クラスの定義、継承、特殊メソッドを学びます",
    order: 11,
    exercises: ex11,
  },
  {
    id: "12-modules",
    title: "モジュールとパッケージ",
    description: "標準ライブラリの活用方法を学びます",
    order: 12,
    exercises: ex12,
  },
  {
    id: "13-exceptions",
    title: "例外処理",
    description: "try-except、カスタム例外を学びます",
    order: 13,
    exercises: ex13,
  },
  {
    id: "14-comprehensions",
    title: "内包表記とジェネレータ",
    description: "リスト・辞書内包表記、ジェネレータ式を学びます",
    order: 14,
    exercises: ex14,
  },
  {
    id: "15-decorators",
    title: "デコレータとジェネレータ",
    description: "デコレータの仕組みとジェネレータ関数を学びます",
    order: 15,
    exercises: ex15,
  },
];

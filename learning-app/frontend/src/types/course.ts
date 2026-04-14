export interface Course {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  lessonCount: number;
  prerequisites: string[];
}

export interface LessonMeta {
  id: string;
  title: string;
  description: string;
  order: number;
  exercises: ExerciseMeta[];
}

export interface ExerciseMeta {
  id: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  executionTarget: "pyodide" | "backend";
  starterCode: string;
  solutionCode: string;
  hints: string[];
  testCases: TestCase[];
}

export interface TestCase {
  id: string;
  description: string;
  type: "stdout" | "return_value" | "variable_check" | "custom";
  expected: string | number | boolean | Record<string, unknown>;
}

export interface CourseWithLessons extends Course {
  lessons: LessonMeta[];
}

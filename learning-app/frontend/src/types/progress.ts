export interface UserProgress {
  version: 1;
  courses: Record<string, CourseProgress>;
}

export interface CourseProgress {
  startedAt: string;
  lessons: Record<string, LessonProgress>;
}

export interface LessonProgress {
  completedAt?: string;
  exercises: Record<string, ExerciseProgress>;
}

export interface ExerciseProgress {
  completedAt?: string;
  attempts: number;
  bestCode?: string;
}

"use client";

import { useState, useEffect, useCallback } from "react";
import type { UserProgress } from "@/types/progress";
import { pythonBasicsLessons } from "@/content/python-basics";
import { machineLearningLessons } from "@/content/machine-learning";
import { deepLearningLessons } from "@/content/deep-learning";
import { generativeAiLessons } from "@/content/generative-ai";

const STORAGE_KEY = "python-learning-progress";

const lessonsMap: Record<string, { exercises: { id: string }[] }[]> = {
  "python-basics": pythonBasicsLessons,
  "machine-learning": machineLearningLessons,
  "deep-learning": deepLearningLessons,
  "generative-ai": generativeAiLessons,
};

function loadProgress(): UserProgress {
  if (typeof window === "undefined") {
    return { version: 1, courses: {} };
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // ignore
  }
  return { version: 1, courses: {} };
}

function saveProgress(progress: UserProgress) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch {
    // ignore
  }
}

export function useProgress() {
  const [progress, setProgress] = useState<UserProgress>({ version: 1, courses: {} });

  useEffect(() => {
    setProgress(loadProgress());
  }, []);

  const markExerciseComplete = useCallback(
    (courseId: string, lessonId: string, exerciseId: string, code: string) => {
      setProgress((prev) => {
        const next = structuredClone(prev);
        if (!next.courses[courseId]) {
          next.courses[courseId] = {
            startedAt: new Date().toISOString(),
            lessons: {},
          };
        }
        if (!next.courses[courseId].lessons[lessonId]) {
          next.courses[courseId].lessons[lessonId] = { exercises: {} };
        }
        const ex = next.courses[courseId].lessons[lessonId].exercises[exerciseId];
        next.courses[courseId].lessons[lessonId].exercises[exerciseId] = {
          completedAt: new Date().toISOString(),
          attempts: (ex?.attempts || 0) + 1,
          bestCode: code,
        };

        // Check if all exercises in this lesson are complete
        const lessonDef = lessonsMap[courseId]?.find(
          (l: { exercises: { id: string }[] }, idx: number) => {
            const lessons = lessonsMap[courseId];
            return lessons[idx] && getLessonId(courseId, idx) === lessonId;
          }
        );
        if (lessonDef) {
          const allComplete = lessonDef.exercises.every(
            (e: { id: string }) => next.courses[courseId].lessons[lessonId].exercises[e.id]?.completedAt
          );
          if (allComplete) {
            next.courses[courseId].lessons[lessonId].completedAt =
              new Date().toISOString();
          }
        }

        saveProgress(next);
        return next;
      });
    },
    []
  );

  const isExerciseCompleted = useCallback(
    (courseId: string, lessonId: string, exerciseId: string) => {
      return !!progress.courses[courseId]?.lessons[lessonId]?.exercises[
        exerciseId
      ]?.completedAt;
    },
    [progress]
  );

  const isLessonCompleted = useCallback(
    (courseId: string, lessonId: string) => {
      return !!progress.courses[courseId]?.lessons[lessonId]?.completedAt;
    },
    [progress]
  );

  const getExerciseAttempts = useCallback(
    (courseId: string, lessonId: string, exerciseId: string) => {
      return (
        progress.courses[courseId]?.lessons[lessonId]?.exercises[exerciseId]
          ?.attempts || 0
      );
    },
    [progress]
  );

  const courseProgress = useCallback(
    (courseId: string): number => {
      const lessons = lessonsMap[courseId];
      if (!lessons) return 0;
      const total = lessons.length;
      const completed = lessons.filter(
        (_: unknown, idx: number) =>
          progress.courses[courseId]?.lessons[getLessonId(courseId, idx)]
            ?.completedAt
      ).length;
      return total > 0 ? Math.round((completed / total) * 100) : 0;
    },
    [progress]
  );

  return {
    progress,
    markExerciseComplete,
    isExerciseCompleted,
    isLessonCompleted,
    getExerciseAttempts,
    courseProgress,
  };
}

function getLessonId(courseId: string, index: number): string {
  const lessons = lessonsMap[courseId];
  if (!lessons || !lessons[index]) return "";
  // Lessons have an `id` field if they're LessonMeta
  const lesson = lessons[index] as unknown as { id: string };
  return lesson.id || "";
}

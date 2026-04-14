"use client";

import { useState, useCallback } from "react";
import { use } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import LessonContent from "@/components/lesson/LessonContent";
import LessonNavigation from "@/components/lesson/LessonNavigation";
import ExercisePanel from "@/components/exercise/ExercisePanel";
import { courses } from "@/content/courses";
import { pythonBasicsLessons } from "@/content/python-basics";
import { useProgress } from "@/hooks/useProgress";
import type { LessonMeta } from "@/types/course";

// Lesson content imports
import { content as content01 } from "@/content/python-basics/lessons/01-hello-world";
import { content as content02 } from "@/content/python-basics/lessons/02-variables";
import { content as content03 } from "@/content/python-basics/lessons/03-data-types";
import { content as content04 } from "@/content/python-basics/lessons/04-conditionals";
import { content as content05 } from "@/content/python-basics/lessons/05-loops";

const lessonsMap: Record<string, LessonMeta[]> = {
  "python-basics": pythonBasicsLessons,
};

const contentMap: Record<string, string> = {
  "python-basics/01-hello-world": content01,
  "python-basics/02-variables": content02,
  "python-basics/03-data-types": content03,
  "python-basics/04-conditionals": content04,
  "python-basics/05-loops": content05,
};

export default function LessonPage({
  params,
}: {
  params: Promise<{ courseId: string; lessonId: string }>;
}) {
  const { courseId, lessonId } = use(params);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { markExerciseComplete, isExerciseCompleted } = useProgress();

  const course = courses.find((c) => c.id === courseId);
  const lessons = lessonsMap[courseId] || [];
  const lesson = lessons.find((l) => l.id === lessonId);
  const lessonContent = contentMap[`${courseId}/${lessonId}`] || "";

  const handleExerciseComplete = useCallback(
    (exerciseId: string, code: string) => {
      markExerciseComplete(courseId, lessonId, exerciseId, code);
    },
    [courseId, lessonId, markExerciseComplete]
  );

  if (!course || !lesson) {
    return (
      <div className="flex items-center justify-center h-full text-ivory-muted">
        レッスンが見つかりません
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-8">
            {/* Breadcrumb */}
            <div className="text-xs text-text-muted mb-6">
              <span className="hover:text-ivory-muted cursor-pointer">
                {course.title}
              </span>
              <span className="mx-2">/</span>
              <span className="text-ivory-muted">{lesson.title}</span>
            </div>

            {/* Lesson content */}
            <LessonContent content={lessonContent} />

            {/* Exercises */}
            {lesson.exercises.length > 0 && (
              <div className="mt-10">
                <h2 className="font-serif text-xl text-gold font-medium mb-4">
                  演習問題
                </h2>
                <div className="space-y-6">
                  {lesson.exercises.map((exercise) => (
                    <ExercisePanel
                      key={exercise.id}
                      exercise={exercise}
                      courseId={courseId}
                      lessonId={lessonId}
                      onComplete={handleExerciseComplete}
                      isCompleted={isExerciseCompleted(
                        courseId,
                        lessonId,
                        exercise.id
                      )}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Navigation */}
            <LessonNavigation
              courseId={courseId}
              currentLessonId={lessonId}
              lessons={lessons}
            />
          </div>
        </main>
      </div>
    </div>
  );
}

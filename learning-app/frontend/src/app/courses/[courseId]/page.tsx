"use client";

import { useState } from "react";
import Link from "next/link";
import { use } from "react";
import { CheckCircle2, Circle, ArrowLeft } from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import ProgressBar from "@/components/progress/ProgressBar";
import { courses } from "@/content/courses";
import { pythonBasicsLessons } from "@/content/python-basics";
import { useProgress } from "@/hooks/useProgress";
import type { LessonMeta } from "@/types/course";

const lessonsMap: Record<string, LessonMeta[]> = {
  "python-basics": pythonBasicsLessons,
};

export default function CoursePage({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const { courseId } = use(params);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isLessonCompleted, courseProgress } = useProgress();

  const course = courses.find((c) => c.id === courseId);
  const lessons = lessonsMap[courseId] || [];

  if (!course) {
    return (
      <div className="flex items-center justify-center h-full text-ivory-muted">
        コースが見つかりません
      </div>
    );
  }

  const progress = courseProgress(courseId);

  return (
    <div className="flex h-full">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-6 py-10">
            {/* Back link */}
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm text-ivory-muted hover:text-gold transition-colors mb-6"
            >
              <ArrowLeft size={14} />
              コース一覧に戻る
            </Link>

            {/* Course header */}
            <div className="mb-8">
              <h1
                className="font-serif text-2xl font-semibold mb-2"
                style={{ color: course.color }}
              >
                {course.title}
              </h1>
              <p className="text-ivory-muted text-sm mb-4">
                {course.description}
              </p>
              <div className="flex items-center gap-3">
                <ProgressBar value={progress} color={course.color} height={6} />
                <span className="text-sm text-text-muted shrink-0">
                  {progress}%
                </span>
              </div>
            </div>

            {/* Lesson list */}
            <div className="space-y-2">
              {lessons.map((lesson, index) => {
                const completed = isLessonCompleted(courseId, lesson.id);
                return (
                  <Link
                    key={lesson.id}
                    href={`/courses/${courseId}/lessons/${lesson.id}`}
                    className="flex items-center gap-4 p-4 bg-bg-panel border border-border rounded-lg hover:bg-bg-elevated hover:border-border-hover transition-all group"
                  >
                    <div className="flex items-center justify-center w-8 h-8 rounded-full border border-border text-sm text-text-muted group-hover:border-border-hover">
                      {completed ? (
                        <CheckCircle2
                          size={20}
                          className="text-success"
                        />
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-ivory group-hover:text-gold transition-colors">
                        {lesson.title}
                      </h3>
                      <p className="text-xs text-text-muted mt-0.5">
                        {lesson.description}
                      </p>
                    </div>
                    <div className="text-xs text-text-muted">
                      {lesson.exercises.length} 問
                    </div>
                  </Link>
                );
              })}
            </div>

            {lessons.length === 0 && (
              <div className="text-center text-ivory-muted py-12">
                <Circle size={48} className="mx-auto text-text-muted mb-3" />
                <p>このコースはまだ準備中です</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

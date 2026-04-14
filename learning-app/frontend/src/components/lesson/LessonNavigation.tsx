"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { LessonMeta } from "@/types/course";

interface LessonNavigationProps {
  courseId: string;
  currentLessonId: string;
  lessons: LessonMeta[];
}

export default function LessonNavigation({
  courseId,
  currentLessonId,
  lessons,
}: LessonNavigationProps) {
  const currentIndex = lessons.findIndex((l) => l.id === currentLessonId);
  const prevLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
  const nextLesson =
    currentIndex < lessons.length - 1 ? lessons[currentIndex + 1] : null;

  return (
    <div className="flex items-center justify-between pt-6 mt-6 border-t border-border">
      {prevLesson ? (
        <Link
          href={`/courses/${courseId}/lessons/${prevLesson.id}`}
          className="flex items-center gap-2 text-sm text-ivory-muted hover:text-gold transition-colors"
        >
          <ChevronLeft size={16} />
          <div>
            <div className="text-xs text-text-muted">前のレッスン</div>
            <div>{prevLesson.title}</div>
          </div>
        </Link>
      ) : (
        <div />
      )}

      {nextLesson ? (
        <Link
          href={`/courses/${courseId}/lessons/${nextLesson.id}`}
          className="flex items-center gap-2 text-sm text-ivory-muted hover:text-gold transition-colors text-right"
        >
          <div>
            <div className="text-xs text-text-muted">次のレッスン</div>
            <div>{nextLesson.title}</div>
          </div>
          <ChevronRight size={16} />
        </Link>
      ) : (
        <div />
      )}
    </div>
  );
}

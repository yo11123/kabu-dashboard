"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Code2,
  BrainCircuit,
  Network,
  Sparkles,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  X,
} from "lucide-react";
import { courses } from "@/content/courses";
import { pythonBasicsLessons } from "@/content/python-basics";
import { machineLearningLessons } from "@/content/machine-learning";
import { deepLearningLessons } from "@/content/deep-learning";
import { generativeAiLessons } from "@/content/generative-ai";
import type { Course, LessonMeta } from "@/types/course";
import { useProgress } from "@/hooks/useProgress";
import { useState } from "react";

const iconMap: Record<string, React.ComponentType<React.SVGProps<SVGSVGElement> & { size?: number }>> = {
  Code2,
  BrainCircuit,
  Network,
  Sparkles,
};

const lessonsMap: Record<string, LessonMeta[]> = {
  "python-basics": pythonBasicsLessons,
  "machine-learning": machineLearningLessons,
  "deep-learning": deepLearningLessons,
  "generative-ai": generativeAiLessons,
};

export default function Sidebar({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const { isLessonCompleted } = useProgress();
  const [expandedCourse, setExpandedCourse] = useState<string | null>(
    "python-basics"
  );

  const toggleCourse = (courseId: string) => {
    setExpandedCourse(expandedCourse === courseId ? null : courseId);
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-72 bg-bg-sidebar border-r border-border flex flex-col transition-transform duration-200 ${
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="p-5 border-b border-border flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2" onClick={onClose}>
            <Code2 size={24} className="text-gold" />
            <h1 className="font-serif text-lg text-gold font-semibold">
              Python学習
            </h1>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden text-ivory-muted hover:text-ivory"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-3">
          {courses.map((course) => (
            <CourseSection
              key={course.id}
              course={course}
              lessons={lessonsMap[course.id]}
              isExpanded={expandedCourse === course.id}
              onToggle={() => toggleCourse(course.id)}
              currentPath={pathname}
              isLessonCompleted={isLessonCompleted}
              onNavigate={onClose}
            />
          ))}
        </nav>
      </aside>
    </>
  );
}

function CourseSection({
  course,
  lessons,
  isExpanded,
  onToggle,
  currentPath,
  isLessonCompleted,
  onNavigate,
}: {
  course: Course;
  lessons?: LessonMeta[];
  isExpanded: boolean;
  onToggle: () => void;
  currentPath: string;
  isLessonCompleted: (courseId: string, lessonId: string) => boolean;
  onNavigate: () => void;
}) {
  const Icon = iconMap[course.icon] || Code2;
  const hasLessons = lessons && lessons.length > 0;

  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-bg-elevated transition-colors ${
          isExpanded ? "text-ivory" : "text-ivory-muted"
        }`}
      >
        <Icon size={18} style={{ color: course.color }} />
        <span className="flex-1 text-left font-medium">{course.title}</span>
        {hasLessons ? (
          isExpanded ? (
            <ChevronDown size={16} className="text-text-muted" />
          ) : (
            <ChevronRight size={16} className="text-text-muted" />
          )
        ) : (
          <span className="text-xs text-text-muted">準備中</span>
        )}
      </button>

      {isExpanded && hasLessons && (
        <div className="ml-4 border-l border-border">
          {lessons.map((lesson) => {
            const href = `/courses/${course.id}/lessons/${lesson.id}`;
            const isActive = currentPath === href;
            const completed = isLessonCompleted(course.id, lesson.id);

            return (
              <Link
                key={lesson.id}
                href={href}
                onClick={onNavigate}
                className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
                  isActive
                    ? "text-gold bg-bg-elevated border-l-2 border-gold -ml-px"
                    : "text-ivory-muted hover:text-ivory hover:bg-bg-elevated"
                }`}
              >
                {completed ? (
                  <CheckCircle2 size={14} className="text-success shrink-0" />
                ) : (
                  <Circle size={14} className="text-text-muted shrink-0" />
                )}
                <span className="truncate">{lesson.title}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

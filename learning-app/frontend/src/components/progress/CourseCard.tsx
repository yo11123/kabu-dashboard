"use client";

import Link from "next/link";
import { Code2, BrainCircuit, Network, Sparkles, Lock } from "lucide-react";
import type { Course } from "@/types/course";
import ProgressBar from "./ProgressBar";

const iconMap: Record<string, React.ComponentType<React.SVGProps<SVGSVGElement> & { size?: number }>> = {
  Code2,
  BrainCircuit,
  Network,
  Sparkles,
};

interface CourseCardProps {
  course: Course;
  progress: number;
  available: boolean;
}

export default function CourseCard({
  course,
  progress,
  available,
}: CourseCardProps) {
  const Icon = iconMap[course.icon] || Code2;

  const content = (
    <div
      className={`group relative border border-border rounded-xl p-6 transition-all duration-200 ${
        available
          ? "bg-bg-panel hover:bg-bg-elevated hover:border-border-hover cursor-pointer"
          : "bg-bg-panel/50 opacity-60"
      }`}
    >
      <div className="flex items-start gap-4">
        <div
          className="p-3 rounded-lg"
          style={{ backgroundColor: `${course.color}10` }}
        >
          <Icon size={24} style={{ color: course.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-ivory text-lg">{course.title}</h3>
            {!available && <Lock size={14} className="text-text-muted" />}
          </div>
          <p className="text-sm text-ivory-muted mt-1 line-clamp-2">
            {course.description}
          </p>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs text-text-muted">
              {course.lessonCount} レッスン
            </span>
            {progress > 0 && (
              <span className="text-xs" style={{ color: course.color }}>
                {progress}% 完了
              </span>
            )}
          </div>
          {available && (
            <div className="mt-3">
              <ProgressBar value={progress} color={course.color} />
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (!available) return content;

  return <Link href={`/courses/${course.id}`}>{content}</Link>;
}

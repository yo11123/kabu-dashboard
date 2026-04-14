"use client";

import { useState } from "react";
import { Code2, BookOpen } from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import CourseCard from "@/components/progress/CourseCard";
import { courses } from "@/content/courses";
import { useProgress } from "@/hooks/useProgress";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { courseProgress } = useProgress();

  return (
    <div className="flex h-full">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-10">
            {/* Hero */}
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 bg-gold/10 rounded-lg">
                  <Code2 size={28} className="text-gold" />
                </div>
                <div>
                  <h1 className="font-serif text-3xl text-gold font-semibold">
                    Python学習ダッシュボード
                  </h1>
                  <p className="text-ivory-muted text-sm mt-1">
                    Python・機械学習・深層学習・生成AIをインタラクティブに学ぶ
                  </p>
                </div>
              </div>
            </div>

            {/* Getting started */}
            <div className="bg-bg-panel border border-border rounded-xl p-6 mb-8">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={18} className="text-sage" />
                <h2 className="text-ivory font-medium">はじめに</h2>
              </div>
              <p className="text-sm text-ivory-muted leading-relaxed">
                このアプリでは、ブラウザ上でPythonコードを書いて実行しながらプログラミングを学べます。
                まずは「Python基礎」コースから始めましょう。各レッスンには解説と演習問題があります。
                コードエディタに解答を書いて「実行」ボタンを押すと、結果がすぐに表示されます。
              </p>
            </div>

            {/* Course list */}
            <h2 className="text-ivory font-medium mb-4">コース一覧</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {courses.map((course) => {
                const available =
                  course.prerequisites.length === 0 ||
                  course.prerequisites.every(
                    (prereq) => courseProgress(prereq) >= 100
                  );
                return (
                  <CourseCard
                    key={course.id}
                    course={course}
                    progress={courseProgress(course.id)}
                    available={true}
                  />
                );
              })}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

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
import { machineLearningLessons } from "@/content/machine-learning";
import { deepLearningLessons } from "@/content/deep-learning";
import { generativeAiLessons } from "@/content/generative-ai";
import { useProgress } from "@/hooks/useProgress";
import type { LessonMeta } from "@/types/course";

// Python basics lesson content
import { content as pb01 } from "@/content/python-basics/lessons/01-hello-world";
import { content as pb02 } from "@/content/python-basics/lessons/02-variables";
import { content as pb03 } from "@/content/python-basics/lessons/03-data-types";
import { content as pb04 } from "@/content/python-basics/lessons/04-conditionals";
import { content as pb05 } from "@/content/python-basics/lessons/05-loops";
import { content as pb06 } from "@/content/python-basics/lessons/06-functions";
import { content as pb07 } from "@/content/python-basics/lessons/07-strings";
import { content as pb08 } from "@/content/python-basics/lessons/08-tuples-sets";
import { content as pb09 } from "@/content/python-basics/lessons/09-dict-advanced";
import { content as pb10 } from "@/content/python-basics/lessons/10-file-io";
import { content as pb11 } from "@/content/python-basics/lessons/11-classes";
import { content as pb12 } from "@/content/python-basics/lessons/12-modules";
import { content as pb13 } from "@/content/python-basics/lessons/13-exceptions";
import { content as pb14 } from "@/content/python-basics/lessons/14-comprehensions";
import { content as pb15 } from "@/content/python-basics/lessons/15-decorators";

// Machine learning lesson content
import { content as ml01 } from "@/content/machine-learning/lessons/01-intro-to-ml";
import { content as ml02 } from "@/content/machine-learning/lessons/02-numpy-pandas";
import { content as ml03 } from "@/content/machine-learning/lessons/03-data-preprocessing";
import { content as ml04 } from "@/content/machine-learning/lessons/04-linear-regression";
import { content as ml05 } from "@/content/machine-learning/lessons/05-logistic-regression";
import { content as ml06 } from "@/content/machine-learning/lessons/06-decision-trees";
import { content as ml07 } from "@/content/machine-learning/lessons/07-random-forests";
import { content as ml08 } from "@/content/machine-learning/lessons/08-svm";
import { content as ml09 } from "@/content/machine-learning/lessons/09-clustering";
import { content as ml10 } from "@/content/machine-learning/lessons/10-evaluation-metrics";
import { content as ml11 } from "@/content/machine-learning/lessons/11-cross-validation";
import { content as ml12 } from "@/content/machine-learning/lessons/12-pipeline";

// Deep learning lesson content
import { content as dl01 } from "@/content/deep-learning/lessons/01-intro-to-dl";
import { content as dl02 } from "@/content/deep-learning/lessons/02-tensors";
import { content as dl03 } from "@/content/deep-learning/lessons/03-autograd";
import { content as dl04 } from "@/content/deep-learning/lessons/04-neural-network";
import { content as dl05 } from "@/content/deep-learning/lessons/05-training-loop";
import { content as dl06 } from "@/content/deep-learning/lessons/06-cnn-basics";
import { content as dl07 } from "@/content/deep-learning/lessons/07-cnn-image-classification";
import { content as dl08 } from "@/content/deep-learning/lessons/08-rnn-basics";
import { content as dl09 } from "@/content/deep-learning/lessons/09-lstm";
import { content as dl10 } from "@/content/deep-learning/lessons/10-transfer-learning";

// Generative AI lesson content
import { content as ga01 } from "@/content/generative-ai/lessons/01-intro-to-genai";
import { content as ga02 } from "@/content/generative-ai/lessons/02-llm-basics";
import { content as ga03 } from "@/content/generative-ai/lessons/03-openai-api";
import { content as ga04 } from "@/content/generative-ai/lessons/04-prompt-engineering";
import { content as ga05 } from "@/content/generative-ai/lessons/05-few-shot-learning";
import { content as ga06 } from "@/content/generative-ai/lessons/06-chain-of-thought";
import { content as ga07 } from "@/content/generative-ai/lessons/07-embeddings";
import { content as ga08 } from "@/content/generative-ai/lessons/08-rag-basics";
import { content as ga09 } from "@/content/generative-ai/lessons/09-building-chatbot";
import { content as ga10 } from "@/content/generative-ai/lessons/10-building-ai-app";

const lessonsMap: Record<string, LessonMeta[]> = {
  "python-basics": pythonBasicsLessons,
  "machine-learning": machineLearningLessons,
  "deep-learning": deepLearningLessons,
  "generative-ai": generativeAiLessons,
};

const contentMap: Record<string, string> = {
  // Python basics
  "python-basics/01-hello-world": pb01,
  "python-basics/02-variables": pb02,
  "python-basics/03-data-types": pb03,
  "python-basics/04-conditionals": pb04,
  "python-basics/05-loops": pb05,
  "python-basics/06-functions": pb06,
  "python-basics/07-strings": pb07,
  "python-basics/08-tuples-sets": pb08,
  "python-basics/09-dict-advanced": pb09,
  "python-basics/10-file-io": pb10,
  "python-basics/11-classes": pb11,
  "python-basics/12-modules": pb12,
  "python-basics/13-exceptions": pb13,
  "python-basics/14-comprehensions": pb14,
  "python-basics/15-decorators": pb15,
  // Machine learning
  "machine-learning/01-intro-to-ml": ml01,
  "machine-learning/02-numpy-pandas": ml02,
  "machine-learning/03-data-preprocessing": ml03,
  "machine-learning/04-linear-regression": ml04,
  "machine-learning/05-logistic-regression": ml05,
  "machine-learning/06-decision-trees": ml06,
  "machine-learning/07-random-forests": ml07,
  "machine-learning/08-svm": ml08,
  "machine-learning/09-clustering": ml09,
  "machine-learning/10-evaluation-metrics": ml10,
  "machine-learning/11-cross-validation": ml11,
  "machine-learning/12-pipeline": ml12,
  // Deep learning
  "deep-learning/01-intro-to-dl": dl01,
  "deep-learning/02-tensors": dl02,
  "deep-learning/03-autograd": dl03,
  "deep-learning/04-neural-network": dl04,
  "deep-learning/05-training-loop": dl05,
  "deep-learning/06-cnn-basics": dl06,
  "deep-learning/07-cnn-image-classification": dl07,
  "deep-learning/08-rnn-basics": dl08,
  "deep-learning/09-lstm": dl09,
  "deep-learning/10-transfer-learning": dl10,
  // Generative AI
  "generative-ai/01-intro-to-genai": ga01,
  "generative-ai/02-llm-basics": ga02,
  "generative-ai/03-openai-api": ga03,
  "generative-ai/04-prompt-engineering": ga04,
  "generative-ai/05-few-shot-learning": ga05,
  "generative-ai/06-chain-of-thought": ga06,
  "generative-ai/07-embeddings": ga07,
  "generative-ai/08-rag-basics": ga08,
  "generative-ai/09-building-chatbot": ga09,
  "generative-ai/10-building-ai-app": ga10,
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

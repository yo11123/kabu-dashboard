"use client";

import { useState, useCallback } from "react";
import { Play, RotateCcw, CheckCheck, Eye, EyeOff } from "lucide-react";
import type { ExerciseMeta } from "@/types/course";
import type { ExecutionResult, TestResult } from "@/types/execution";
import { usePyodide } from "@/hooks/usePyodide";
import CodeEditor from "./CodeEditor";
import OutputPanel from "./OutputPanel";
import HintAccordion from "./HintAccordion";

interface ExercisePanelProps {
  exercise: ExerciseMeta;
  courseId: string;
  lessonId: string;
  onComplete?: (exerciseId: string, code: string) => void;
  isCompleted?: boolean;
}

const difficultyLabel: Record<string, { text: string; color: string }> = {
  easy: { text: "初級", color: "text-success" },
  medium: { text: "中級", color: "text-warning" },
  hard: { text: "上級", color: "text-error" },
};

export default function ExercisePanel({
  exercise,
  onComplete,
  isCompleted: initialCompleted = false,
}: ExercisePanelProps) {
  const [code, setCode] = useState(exercise.starterCode);
  const [executionResult, setExecutionResult] =
    useState<ExecutionResult | null>(null);
  const [testResults, setTestResults] = useState<TestResult[] | null>(null);
  const [showSolution, setShowSolution] = useState(false);
  const [isCompleted, setIsCompleted] = useState(initialCompleted);

  const { status, execute, checkAnswer } = usePyodide();

  const handleRun = useCallback(async () => {
    setTestResults(null);
    const result = await execute(code);
    setExecutionResult(result);
  }, [code, execute]);

  const handleCheck = useCallback(async () => {
    setExecutionResult(null);
    const result = await checkAnswer(code, exercise.testCases);
    setTestResults(result.results);
    if (result.allPassed && !isCompleted) {
      setIsCompleted(true);
      onComplete?.(exercise.id, code);
    }
  }, [code, exercise, checkAnswer, isCompleted, onComplete]);

  const handleReset = () => {
    setCode(exercise.starterCode);
    setExecutionResult(null);
    setTestResults(null);
  };

  const diff = difficultyLabel[exercise.difficulty];

  return (
    <div className="border border-border rounded-lg bg-bg-panel overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-bg-elevated">
        <h3 className="text-sm font-medium text-ivory flex-1">
          {exercise.title}
        </h3>
        <span className={`text-xs font-medium ${diff.color}`}>{diff.text}</span>
        {isCompleted && (
          <span className="text-xs font-medium text-success flex items-center gap-1">
            <CheckCheck size={14} /> 完了
          </span>
        )}
      </div>

      {/* Editor */}
      <div className="p-3">
        <CodeEditor
          value={code}
          onChange={setCode}
          onRun={handleRun}
          height="180px"
        />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 px-3 pb-3">
        <button
          onClick={handleRun}
          disabled={status === "running" || status === "loading"}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gold/10 text-gold hover:bg-gold/20 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Play size={14} />
          実行
        </button>
        <button
          onClick={handleCheck}
          disabled={status === "running" || status === "loading"}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-sage/10 text-sage hover:bg-sage/20 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
        >
          <CheckCheck size={14} />
          解答チェック
        </button>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 px-3 py-1.5 text-text-muted hover:text-ivory hover:bg-bg-elevated rounded-md text-sm transition-colors"
        >
          <RotateCcw size={14} />
          リセット
        </button>
        <button
          onClick={() => setShowSolution(!showSolution)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-text-muted hover:text-ivory hover:bg-bg-elevated rounded-md text-sm transition-colors ml-auto"
        >
          {showSolution ? <EyeOff size={14} /> : <Eye size={14} />}
          {showSolution ? "解答を隠す" : "解答を見る"}
        </button>
      </div>

      {/* Solution */}
      {showSolution && (
        <div className="px-3 pb-3">
          <div className="border border-gold/20 rounded-lg overflow-hidden">
            <div className="px-3 py-1.5 bg-gold/5 text-xs text-gold font-medium">
              解答例
            </div>
            <CodeEditor
              value={exercise.solutionCode}
              onChange={() => {}}
              readOnly
              height="120px"
            />
          </div>
        </div>
      )}

      {/* Hints */}
      <div className="px-3 pb-3">
        <HintAccordion hints={exercise.hints} />
      </div>

      {/* Output */}
      <div className="px-3 pb-3">
        <OutputPanel
          executionResult={executionResult}
          testResults={testResults}
          status={status}
        />
      </div>
    </div>
  );
}

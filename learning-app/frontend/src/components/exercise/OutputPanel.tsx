"use client";

import { CheckCircle2, XCircle, Terminal, AlertTriangle } from "lucide-react";
import type { ExecutionResult, TestResult, ExecutionStatus } from "@/types/execution";

interface OutputPanelProps {
  executionResult: ExecutionResult | null;
  testResults: TestResult[] | null;
  status: ExecutionStatus;
}

export default function OutputPanel({
  executionResult,
  testResults,
  status,
}: OutputPanelProps) {
  if (status === "loading") {
    return (
      <div className="bg-bg-panel border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gold text-sm">
          <div className="animate-spin h-4 w-4 border-2 border-gold border-t-transparent rounded-full" />
          <span>Pythonエンジンを読み込み中...</span>
        </div>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="bg-bg-panel border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gold text-sm">
          <div className="animate-spin h-4 w-4 border-2 border-gold border-t-transparent rounded-full" />
          <span>実行中...</span>
        </div>
      </div>
    );
  }

  const hasOutput = executionResult?.stdout || executionResult?.stderr || executionResult?.error;

  return (
    <div className="bg-bg-panel border border-border rounded-lg overflow-hidden">
      {/* Execution output */}
      {hasOutput && (
        <div className="border-b border-border">
          <div className="flex items-center gap-2 px-3 py-2 bg-bg-elevated">
            <Terminal size={14} className="text-text-muted" />
            <span className="text-xs text-text-muted font-medium">出力</span>
          </div>
          <div className="p-3 font-mono text-sm max-h-48 overflow-y-auto">
            {executionResult?.stdout && (
              <pre className="text-ivory whitespace-pre-wrap">
                {executionResult.stdout}
              </pre>
            )}
            {(executionResult?.stderr || executionResult?.error) && (
              <pre className="text-error whitespace-pre-wrap">
                {executionResult.stderr || executionResult.error}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Test results */}
      {testResults && testResults.length > 0 && (
        <div>
          <div className="flex items-center gap-2 px-3 py-2 bg-bg-elevated">
            {testResults.every((r) => r.passed) ? (
              <CheckCircle2 size={14} className="text-success" />
            ) : (
              <AlertTriangle size={14} className="text-error" />
            )}
            <span className="text-xs text-text-muted font-medium">
              テスト結果
            </span>
            <span className="text-xs text-text-muted ml-auto">
              {testResults.filter((r) => r.passed).length}/{testResults.length}{" "}
              合格
            </span>
          </div>
          <div className="p-3 space-y-2">
            {testResults.map((result) => (
              <div key={result.id} className="flex items-start gap-2 text-sm">
                {result.passed ? (
                  <CheckCircle2
                    size={16}
                    className="text-success shrink-0 mt-0.5"
                  />
                ) : (
                  <XCircle
                    size={16}
                    className="text-error shrink-0 mt-0.5"
                  />
                )}
                <div>
                  <span
                    className={
                      result.passed ? "text-success" : "text-error"
                    }
                  >
                    {result.description}
                  </span>
                  {result.error && (
                    <p className="text-xs text-error/70 mt-0.5 font-mono">
                      {result.error}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!hasOutput && !testResults && status === "idle" && (
        <div className="p-4 text-center text-text-muted text-sm">
          「実行」ボタンを押すか Ctrl+Enter でコードを実行できます
        </div>
      )}
    </div>
  );
}

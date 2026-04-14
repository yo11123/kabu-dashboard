"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { ExecutionResult, ExecutionStatus, TestResult } from "@/types/execution";
import type { TestCase } from "@/types/course";

let workerInstance: Worker | null = null;
let requestId = 0;

function getWorker(): Worker {
  if (!workerInstance) {
    workerInstance = new Worker("/pyodide-worker.js");
  }
  return workerInstance;
}

export function usePyodide() {
  const [status, setStatus] = useState<ExecutionStatus>("idle");
  const [pyodideReady, setPyodideReady] = useState(false);
  const callbacksRef = useRef<
    Map<number, { resolve: (value: unknown) => void; reject: (reason: unknown) => void }>
  >(new Map());

  useEffect(() => {
    const worker = getWorker();

    const handler = (event: MessageEvent) => {
      const { type, id, data } = event.data;

      if (type === "init-complete") {
        setPyodideReady(true);
        const cb = callbacksRef.current.get(id);
        if (cb) {
          cb.resolve(undefined);
          callbacksRef.current.delete(id);
        }
        return;
      }

      if (type === "result" || type === "check-result" || type === "error") {
        const cb = callbacksRef.current.get(id);
        if (cb) {
          if (type === "error") {
            cb.resolve({ success: false, stdout: "", stderr: data, error: data });
          } else {
            cb.resolve(data);
          }
          callbacksRef.current.delete(id);
        }
      }
    };

    worker.addEventListener("message", handler);
    return () => {
      worker.removeEventListener("message", handler);
    };
  }, []);

  const sendMessage = useCallback(
    (type: string, payload: unknown): Promise<unknown> => {
      return new Promise((resolve, reject) => {
        const id = ++requestId;
        callbacksRef.current.set(id, { resolve, reject });
        const worker = getWorker();
        worker.postMessage({ type, payload, id });
      });
    },
    []
  );

  const initPyodide = useCallback(async () => {
    if (pyodideReady) return;
    setStatus("loading");
    await sendMessage("init", {});
    setStatus("idle");
  }, [pyodideReady, sendMessage]);

  const execute = useCallback(
    async (code: string): Promise<ExecutionResult> => {
      setStatus("running");
      try {
        if (!pyodideReady) {
          await initPyodide();
        }
        const result = (await sendMessage("execute", { code })) as {
          success: boolean;
          stdout: string;
          stderr: string;
          error?: string;
        };
        setStatus(result.success ? "success" : "error");
        return {
          stdout: result.stdout,
          stderr: result.stderr,
          error: result.error,
        };
      } catch (err) {
        setStatus("error");
        return {
          stdout: "",
          stderr: String(err),
          error: String(err),
        };
      }
    },
    [pyodideReady, initPyodide, sendMessage]
  );

  const checkAnswer = useCallback(
    async (
      code: string,
      testCases: TestCase[]
    ): Promise<{ results: TestResult[]; allPassed: boolean }> => {
      setStatus("running");
      try {
        if (!pyodideReady) {
          await initPyodide();
        }

        const serializedTestCases = testCases.map((tc) => ({
          id: tc.id,
          description: tc.description,
          type: tc.type,
          expected: tc.expected,
        }));

        const result = (await sendMessage("check", {
          code,
          testCases: serializedTestCases,
        })) as {
          results: TestResult[];
          allPassed: boolean;
          error?: string;
          passed?: boolean;
        };

        if (result.error !== undefined && result.passed !== undefined) {
          // Single error result
          setStatus("error");
          return {
            results: [
              {
                id: "error",
                description: "実行エラー",
                passed: false,
                error: result.error,
              },
            ],
            allPassed: false,
          };
        }

        setStatus(result.allPassed ? "success" : "error");
        return result;
      } catch (err) {
        setStatus("error");
        return {
          results: [
            {
              id: "error",
              description: "実行エラー",
              passed: false,
              error: String(err),
            },
          ],
          allPassed: false,
        };
      }
    },
    [pyodideReady, initPyodide, sendMessage]
  );

  return {
    status,
    pyodideReady,
    initPyodide,
    execute,
    checkAnswer,
  };
}

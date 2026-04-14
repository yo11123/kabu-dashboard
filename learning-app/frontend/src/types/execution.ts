export type ExecutionStatus = "idle" | "loading" | "running" | "success" | "error";

export interface ExecutionResult {
  stdout: string;
  stderr: string;
  error?: string;
  figures?: string[];
  executionTimeMs?: number;
}

export interface TestResult {
  id: string;
  description: string;
  passed: boolean;
  actual?: string;
  error?: string;
}

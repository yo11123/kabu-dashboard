// Pyodide Web Worker - runs Python code in a sandboxed environment
let pyodide = null;
let isInitializing = false;

async function initPyodide() {
  if (pyodide) return pyodide;
  if (isInitializing) {
    // Wait for initialization to complete
    while (isInitializing) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return pyodide;
  }

  isInitializing = true;
  try {
    importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.5/full/pyodide.js");
    pyodide = await loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/",
    });
    isInitializing = false;
    return pyodide;
  } catch (error) {
    isInitializing = false;
    throw error;
  }
}

self.onmessage = async function (event) {
  const { type, payload, id } = event.data;

  if (type === "init") {
    try {
      await initPyodide();
      self.postMessage({ type: "init-complete", id });
    } catch (error) {
      self.postMessage({
        type: "error",
        data: `Pyodideの初期化に失敗しました: ${error.message}`,
        id,
      });
    }
    return;
  }

  if (type === "execute") {
    try {
      const py = await initPyodide();

      // Reset stdout/stderr
      py.runPython(`
import sys
import io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
`);

      // Load packages if needed
      if (payload.packages && payload.packages.length > 0) {
        await py.loadPackagesFromImports(payload.code);
      }

      // Execute user code
      try {
        py.runPython(payload.code);
      } catch (pyError) {
        const stderr = py.runPython("sys.stderr.getvalue()");
        const stdout = py.runPython("sys.stdout.getvalue()");
        self.postMessage({
          type: "result",
          id,
          data: {
            success: false,
            stdout: stdout || "",
            stderr: stderr || pyError.message,
            error: pyError.message,
          },
        });
        return;
      }

      const stdout = py.runPython("sys.stdout.getvalue()");
      const stderr = py.runPython("sys.stderr.getvalue()");

      self.postMessage({
        type: "result",
        id,
        data: {
          success: true,
          stdout: stdout || "",
          stderr: stderr || "",
        },
      });
    } catch (error) {
      self.postMessage({
        type: "error",
        data: error.message,
        id,
      });
    }
    return;
  }

  if (type === "check") {
    try {
      const py = await initPyodide();

      // Reset stdout/stderr and run user code
      py.runPython(`
import sys
import io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
`);

      try {
        py.runPython(payload.code);
      } catch (pyError) {
        self.postMessage({
          type: "check-result",
          id,
          data: {
            passed: false,
            error: `コードの実行中にエラーが発生しました: ${pyError.message}`,
          },
        });
        return;
      }

      // Run test cases
      const results = [];
      for (const tc of payload.testCases) {
        try {
          if (tc.type === "stdout") {
            const stdout = py.runPython("sys.stdout.getvalue()");
            const passed = stdout === tc.expected;
            results.push({
              id: tc.id,
              description: tc.description,
              passed,
              actual: stdout,
              error: passed
                ? undefined
                : `期待: "${tc.expected.replace(/\n/g, "\\n")}" / 実際: "${stdout.replace(/\n/g, "\\n")}"`,
            });
          } else if (tc.type === "custom") {
            try {
              py.runPython(tc.expected.checkCode);
              results.push({
                id: tc.id,
                description: tc.description,
                passed: true,
              });
            } catch (assertError) {
              results.push({
                id: tc.id,
                description: tc.description,
                passed: false,
                error: assertError.message,
              });
            }
          }
        } catch (testError) {
          results.push({
            id: tc.id,
            description: tc.description,
            passed: false,
            error: testError.message,
          });
        }
      }

      self.postMessage({
        type: "check-result",
        id,
        data: {
          results,
          allPassed: results.every((r) => r.passed),
        },
      });
    } catch (error) {
      self.postMessage({
        type: "error",
        data: error.message,
        id,
      });
    }
  }
};

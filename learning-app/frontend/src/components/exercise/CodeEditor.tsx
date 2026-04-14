"use client";

import { useRef, useCallback } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  onRun?: () => void;
  readOnly?: boolean;
  height?: string;
}

export default function CodeEditor({
  value,
  onChange,
  onRun,
  readOnly = false,
  height = "200px",
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;

      // Define custom dark theme
      monaco.editor.defineTheme("kabu-dark", {
        base: "vs-dark",
        inherit: true,
        rules: [
          { token: "keyword", foreground: "d4af37", fontStyle: "bold" },
          { token: "string", foreground: "8fb8a0" },
          { token: "number", foreground: "7b9ed4" },
          { token: "comment", foreground: "6b7280", fontStyle: "italic" },
          { token: "function", foreground: "e6c34d" },
          { token: "variable", foreground: "f0ece4" },
          { token: "type", foreground: "c49ed4" },
          { token: "operator", foreground: "b8b0a2" },
          { token: "delimiter", foreground: "b8b0a2" },
        ],
        colors: {
          "editor.background": "#0a0f1a",
          "editor.foreground": "#f0ece4",
          "editor.lineHighlightBackground": "#0e1320",
          "editor.selectionBackground": "#d4af3730",
          "editor.inactiveSelectionBackground": "#d4af3715",
          "editorCursor.foreground": "#d4af37",
          "editorLineNumber.foreground": "#6b7280",
          "editorLineNumber.activeForeground": "#d4af37",
          "editor.selectionHighlightBackground": "#d4af3715",
          "editorIndentGuide.background": "#1a1f2e",
          "editorIndentGuide.activeBackground": "#2a2f3e",
          "editorWidget.background": "#0a0f1a",
          "editorWidget.border": "#d4af3720",
          "editorSuggestWidget.background": "#0a0f1a",
          "editorSuggestWidget.border": "#d4af3720",
          "editorSuggestWidget.selectedBackground": "#0e1320",
        },
      });

      monaco.editor.setTheme("kabu-dark");

      // Add Ctrl+Enter keybinding
      if (onRun) {
        editor.addAction({
          id: "run-code",
          label: "Run Code",
          keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
          run: () => onRun(),
        });
      }
    },
    [onRun]
  );

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <Editor
        height={height}
        defaultLanguage="python"
        value={value}
        onChange={(v) => onChange(v || "")}
        onMount={handleMount}
        theme="kabu-dark"
        options={{
          fontSize: 14,
          fontFamily: "'IBM Plex Mono', Consolas, monospace",
          minimap: { enabled: false },
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          readOnly,
          automaticLayout: true,
          tabSize: 4,
          insertSpaces: true,
          wordWrap: "on",
          padding: { top: 12, bottom: 12 },
          renderLineHighlight: "line",
          overviewRulerLanes: 0,
          hideCursorInOverviewRuler: true,
          overviewRulerBorder: false,
          scrollbar: {
            verticalScrollbarSize: 6,
            horizontalScrollbarSize: 6,
          },
        }}
        loading={
          <div className="flex items-center justify-center h-full bg-bg-panel text-text-muted text-sm">
            エディタを読み込み中...
          </div>
        }
      />
    </div>
  );
}

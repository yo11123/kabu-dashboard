"use client";

import { useMemo } from "react";

interface LessonContentProps {
  content: string;
}

export default function LessonContent({ content }: LessonContentProps) {
  const html = useMemo(() => parseMarkdown(content), [content]);

  return (
    <div
      className="lesson-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function parseMarkdown(md: string): string {
  let html = md;

  // Code blocks (```python ... ```)
  html = html.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (_match, lang, code) => {
      const escapedCode = escapeHtml(code.trim());
      return `<div class="my-4 rounded-lg overflow-hidden border border-[rgba(212,175,55,0.08)]">
        <div class="flex items-center px-3 py-1.5 bg-[#0e1320] text-xs text-[#6b7280]">
          <span>${lang || "code"}</span>
        </div>
        <pre class="p-4 bg-[#0a0f1a] overflow-x-auto"><code class="text-[#f0ece4] text-sm leading-relaxed">${escapedCode}</code></pre>
      </div>`;
    }
  );

  // Tables
  html = html.replace(
    /\n(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g,
    (_match, headerRow, _sep, bodyRows) => {
      const headers = headerRow
        .split("|")
        .filter((c: string) => c.trim())
        .map((c: string) => `<th class="px-3 py-2 text-left text-xs font-medium text-gold border-b border-[rgba(212,175,55,0.08)]">${c.trim()}</th>`)
        .join("");
      const rows = bodyRows
        .trim()
        .split("\n")
        .map((row: string) => {
          const cells = row
            .split("|")
            .filter((c: string) => c.trim())
            .map((c: string) => `<td class="px-3 py-2 text-sm text-ivory-muted border-b border-[rgba(212,175,55,0.04)]">${inlineFormat(c.trim())}</td>`)
            .join("");
          return `<tr class="hover:bg-[#0e1320]">${cells}</tr>`;
        })
        .join("");
      return `<div class="my-4 overflow-x-auto rounded-lg border border-[rgba(212,175,55,0.08)]"><table class="w-full"><thead class="bg-[#0e1320]"><tr>${headers}</tr></thead><tbody>${rows}</tbody></table></div>`;
    }
  );

  // Blockquotes
  html = html.replace(
    /^> (.+)$/gm,
    '<blockquote>$1</blockquote>'
  );
  // Merge adjacent blockquotes
  html = html.replace(/<\/blockquote>\n<blockquote>/g, "\n");

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Unordered lists
  html = html.replace(
    /(?:^- .+\n?)+/gm,
    (match) => {
      const items = match
        .trim()
        .split("\n")
        .map((line) => `<li>${inlineFormat(line.replace(/^- /, ""))}</li>`)
        .join("");
      return `<ul>${items}</ul>`;
    }
  );

  // Paragraphs (lines that don't start with HTML)
  html = html.replace(/^(?!<[a-z/])(?!$)(.+)$/gm, (_, line) => {
    return `<p>${inlineFormat(line)}</p>`;
  });

  // Clean up empty lines
  html = html.replace(/\n{3,}/g, "\n\n");

  return html;
}

function inlineFormat(text: string): string {
  // Inline code
  text = text.replace(
    /`([^`]+)`/g,
    '<code>$1</code>'
  );
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return text;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

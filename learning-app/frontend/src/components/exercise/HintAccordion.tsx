"use client";

import { useState } from "react";
import { Lightbulb, ChevronDown, ChevronRight } from "lucide-react";

interface HintAccordionProps {
  hints: string[];
}

export default function HintAccordion({ hints }: HintAccordionProps) {
  const [revealedCount, setRevealedCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  if (hints.length === 0) return null;

  const revealNext = () => {
    if (revealedCount < hints.length) {
      setRevealedCount(revealedCount + 1);
      setIsOpen(true);
    }
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => {
          if (revealedCount === 0) {
            revealNext();
          } else {
            setIsOpen(!isOpen);
          }
        }}
        className="w-full flex items-center gap-2 px-3 py-2 bg-bg-elevated hover:bg-bg-panel transition-colors text-sm"
      >
        <Lightbulb size={14} className="text-warning" />
        <span className="text-ivory-muted">ヒント</span>
        {revealedCount > 0 && (
          <span className="text-xs text-text-muted">
            ({revealedCount}/{hints.length})
          </span>
        )}
        <span className="ml-auto">
          {isOpen ? (
            <ChevronDown size={14} className="text-text-muted" />
          ) : (
            <ChevronRight size={14} className="text-text-muted" />
          )}
        </span>
      </button>

      {isOpen && revealedCount > 0 && (
        <div className="px-3 py-2 space-y-2">
          {hints.slice(0, revealedCount).map((hint, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="text-warning font-mono text-xs mt-0.5">
                {i + 1}.
              </span>
              <span className="text-ivory-muted">{hint}</span>
            </div>
          ))}
          {revealedCount < hints.length && (
            <button
              onClick={revealNext}
              className="text-xs text-gold hover:text-gold-light transition-colors"
            >
              次のヒントを表示
            </button>
          )}
        </div>
      )}
    </div>
  );
}

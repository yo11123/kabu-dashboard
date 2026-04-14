"use client";

import { Menu, BookOpen } from "lucide-react";

export default function Header({ onMenuToggle }: { onMenuToggle: () => void }) {
  return (
    <header className="h-12 bg-bg-panel border-b border-border flex items-center px-4 lg:hidden shrink-0">
      <button
        onClick={onMenuToggle}
        className="text-ivory-muted hover:text-ivory mr-3"
      >
        <Menu size={20} />
      </button>
      <div className="flex items-center gap-2">
        <BookOpen size={18} className="text-gold" />
        <span className="text-sm font-medium text-ivory">Python学習</span>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, Settings as SettingsIcon, BarChart3 } from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "ホーム", icon: Home },
  { href: "/stock/7203", label: "サンプル銘柄", icon: BarChart3 },
  { href: "/settings", label: "設定", icon: SettingsIcon },
];

export function PCShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen">
      <aside
        className="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] px-4 py-6"
        aria-label="ナビゲーション"
      >
        <Link href="/" className="block px-2 mb-8">
          <div className="font-serif text-2xl tracking-tight">Kabu</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--text-faint)]">
            v2 · Phase 1
          </div>
        </Link>

        <nav className="space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/" && pathname?.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  active
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]",
                )}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 px-3">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs text-[var(--text-faint)] hover:text-[var(--accent)]"
          >
            <Search size={14} /> 銘柄を検索
          </Link>
        </div>
      </aside>

      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}

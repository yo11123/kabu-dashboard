"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, Settings as SettingsIcon } from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "ホーム", icon: Home },
  { href: "/?focus=1", label: "検索", icon: Search },
  { href: "/settings", label: "設定", icon: SettingsIcon },
];

export function MobileShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-1 pb-20">{children}</main>

      <nav
        aria-label="ボトムナビ"
        className="fixed bottom-0 inset-x-0 z-40 border-t border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur"
      >
        <ul className="grid grid-cols-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const base = href.split("?")[0];
            const active = pathname === base || (base !== "/" && pathname?.startsWith(base));
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex flex-col items-center justify-center py-2 gap-0.5 text-[11px]",
                    active ? "text-[var(--accent)]" : "text-[var(--text-dim)]",
                  )}
                >
                  <Icon size={20} />
                  <span>{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

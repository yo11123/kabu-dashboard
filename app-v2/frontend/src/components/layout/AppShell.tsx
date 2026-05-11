"use client";

import { useIsMobile } from "@/hooks/useBreakpoint";
import { PCShell } from "./PCShell";
import { MobileShell } from "./MobileShell";

export function AppShell({ children }: { children: React.ReactNode }) {
  const isMobile = useIsMobile();
  return isMobile ? <MobileShell>{children}</MobileShell> : <PCShell>{children}</PCShell>;
}

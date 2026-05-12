"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { applyTheme } from "@/lib/themes";
import { useSettings } from "@/stores/settings";

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
      }),
  );

  const theme = useSettings((s) => s.theme);
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

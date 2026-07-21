'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';

import { telegramReady } from '@/lib/telegram';

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: false } },
      })
  );
  useEffect(() => {
    telegramReady();
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

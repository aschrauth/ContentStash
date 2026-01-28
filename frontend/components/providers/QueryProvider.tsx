'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

// Global QueryClient instance that can be accessed from anywhere
let globalQueryClient: QueryClient | null = null;

export function getQueryClient(): QueryClient | null {
  return globalQueryClient;
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => {
      const client = new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30000, // 30 seconds
            gcTime: 300000, // 5 minutes (formerly cacheTime)
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      });
      
      // Store globally for access from Zustand store
      globalQueryClient = client;
      
      return client;
    }
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
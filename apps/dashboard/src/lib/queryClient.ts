import { QueryClient, type QueryClientConfig } from "@tanstack/react-query";

const WILQ_QUERY_STALE_TIME_MS = 30_000;

export function createWilqQueryClient(config?: QueryClientConfig): QueryClient {
  return new QueryClient({
    ...config,
    defaultOptions: {
      ...config?.defaultOptions,
      queries: {
        staleTime: WILQ_QUERY_STALE_TIME_MS,
        gcTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
        ...config?.defaultOptions?.queries
      },
      mutations: {
        ...config?.defaultOptions?.mutations
      }
    }
  });
}

export const queryClient = createWilqQueryClient();

'use client';

import { InfiniteData, useInfiniteQuery, useQueryClient, UseInfiniteQueryResult } from '@tanstack/react-query';
import { getItems, normalizeSavedItem, PaginatedResponse, RawSavedItem } from '@/lib/api';
import { SavedItem } from '@/lib/store';
import { useStore } from '@/lib/store';

interface UseItemsOptions {
  search?: string;
  tags?: string[];
  enabled?: boolean;
}

type ItemsInfiniteData = InfiniteData<PaginatedResponse<SavedItem>, string | undefined>;

/**
 * Hook to fetch items with React Query's useInfiniteQuery for proper infinite scroll
 * This automatically handles pagination, caching, and state persistence across navigation
 */
export function useItems(options: UseItemsOptions = {}): UseInfiniteQueryResult<PaginatedResponse<SavedItem>, Error> {
  const token = useStore((state) => state.token);
  const userId = useStore((state) => state.currentUser?.id);
  const { search, tags, enabled = true } = options;

  return useInfiniteQuery({
    queryKey: ['items', userId, search, tags],
    queryFn: async ({ pageParam }: { pageParam: string | undefined }) => {
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await getItems(token, search, tags, 20, pageParam as string | undefined);

      // Handle both old format (array) and new format (object with pagination)
      let itemsData: RawSavedItem[];
      let pagination: { next_cursor: string | null; has_more: boolean; limit: number; total: number };

      if (Array.isArray(response)) {
        // Old format - backward compatibility
        itemsData = response;
        pagination = { next_cursor: null, has_more: false, limit: 20, total: response.length };
      } else {
        // New format with pagination
        itemsData = response.items;
        pagination = response.pagination;
      }

      // Convert snake_case to camelCase for all items
      const formattedItems: SavedItem[] = itemsData.map(normalizeSavedItem);

      return {
        items: formattedItems,
        pagination,
      };
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      // Return the next cursor if there are more pages, otherwise undefined
      return lastPage.pagination.has_more ? (lastPage.pagination.next_cursor ?? undefined) : undefined;
    },
    enabled: enabled && !!token,
    refetchOnMount: 'always',
    staleTime: 5 * 60 * 1000, // 5 minutes - keep data fresh longer
    gcTime: 10 * 60 * 1000, // 10 minutes - keep in cache longer for navigation
  });
}

/**
 * Hook to invalidate items cache
 */
export function useInvalidateItems() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: ['items'] });
  };
}

/**
 * Hook to manually update items cache (optimistic updates)
 */
export function useUpdateItemsCache() {
  const queryClient = useQueryClient();

  return {
    addItem: (newItem: SavedItem) => {
      queryClient.setQueriesData<ItemsInfiniteData>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData || !oldData.pages || oldData.pages.length === 0) return oldData;

          // Add to the first page
          const newPages = [...oldData.pages];
          newPages[0] = {
            ...newPages[0],
            items: [newItem, ...newPages[0].items],
            pagination: {
              ...newPages[0].pagination,
              total: newPages[0].pagination.total + 1,
            },
          };

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );
    },

    updateItem: (itemId: string, updates: Partial<SavedItem>) => {
      queryClient.setQueriesData<ItemsInfiniteData>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData || !oldData.pages) return oldData;

          const newPages = oldData.pages.map((page) => ({
            ...page,
            items: page.items.map((item) =>
              item.id === itemId ? { ...item, ...updates } : item
            ),
          }));

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );
    },

    removeItem: (itemId: string) => {
      queryClient.setQueriesData<ItemsInfiniteData>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData || !oldData.pages) return oldData;

          const newPages = oldData.pages.map((page) => ({
            ...page,
            items: page.items.filter((item) => item.id !== itemId),
            pagination: {
              ...page.pagination,
              total: Math.max(0, page.pagination.total - 1),
            },
          }));

          return {
            ...oldData,
            pages: newPages,
          };
        }
      );
    },
  };
}

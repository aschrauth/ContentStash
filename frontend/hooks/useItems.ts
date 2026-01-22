'use client';

import { useQuery, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { getItems, PaginatedResponse } from '@/lib/api';
import { SavedItem } from '@/lib/store';
import { useStore } from '@/lib/store';

interface UseItemsOptions {
  search?: string;
  tags?: string[];
  cursor?: string;
  enabled?: boolean;
}

/**
 * Hook to fetch items with React Query for automatic request deduplication
 */
export function useItems(options: UseItemsOptions = {}): UseQueryResult<PaginatedResponse<SavedItem>, Error> {
  const token = useStore((state) => state.token);
  const { search, tags, cursor, enabled = true } = options;

  return useQuery({
    queryKey: ['items', search, tags, cursor],
    queryFn: async () => {
      if (!token) {
        throw new Error('Not authenticated');
      }
      
      const response = await getItems(token, search, tags, 50, cursor);
      
      // Handle both old format (array) and new format (object with pagination)
      let itemsData: any[];
      let pagination: { next_cursor: string | null; has_more: boolean; limit: number };
      
      if (Array.isArray(response)) {
        // Old format - backward compatibility
        itemsData = response;
        pagination = { next_cursor: null, has_more: false, limit: 50 };
      } else {
        // New format with pagination
        itemsData = response.items;
        pagination = response.pagination;
      }
      
      // Convert snake_case to camelCase for all items
      const formattedItems: SavedItem[] = itemsData.map((item: Record<string, unknown>) => ({
        id: item.id as string,
        ownerId: item.owner_id as string,
        url: item.url as string | undefined,
        title: item.title as string,
        description: item.description as string | undefined,
        imageUrl: item.image_url as string | undefined,
        faviconUrl: item.favicon_url as string | undefined,
        notesMarkdown: item.notes_markdown as string | undefined,
        tags: (item.tags as string[]) || [],
        suggestedTags: item.suggested_tags as string[] | undefined,
        suggestedTopic: item.suggested_topic as string | undefined,
        archivedText: item.archived_text as string | undefined,
        extractionType: item.extraction_type as 'fast' | 'complete' | 'local' | undefined,
        processingStatus: item.processing_status as 'pending' | 'processed' | 'failed',
        createdAt: item.created_at as string,
        updatedAt: item.updated_at as string,
        archivedAt: item.archived_at as string | undefined,
      }));
      
      return {
        items: formattedItems,
        pagination,
      };
    },
    enabled: enabled && !!token,
    staleTime: 30000, // 30 seconds
    gcTime: 300000, // 5 minutes
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
      queryClient.setQueriesData<PaginatedResponse<SavedItem>>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            items: [newItem, ...oldData.items],
          };
        }
      );
    },
    
    updateItem: (itemId: string, updates: Partial<SavedItem>) => {
      queryClient.setQueriesData<PaginatedResponse<SavedItem>>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            items: oldData.items.map((item) =>
              item.id === itemId ? { ...item, ...updates } : item
            ),
          };
        }
      );
    },
    
    removeItem: (itemId: string) => {
      queryClient.setQueriesData<PaginatedResponse<SavedItem>>(
        { queryKey: ['items'] },
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            items: oldData.items.filter((item) => item.id !== itemId),
          };
        }
      );
    },
  };
}
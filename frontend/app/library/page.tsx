"use client";

import React, { useState, useMemo, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Filter, Grid, List, Search, Loader2 } from 'lucide-react';
import { useStore } from '@/lib/store';
import { getItems, isApiError, RawSavedItem } from '@/lib/api';
import { resolveItemReadState } from '@/lib/readStatus';
import { cn } from '@/lib/utils';
import AppLayout from '@/components/layout/AppLayout';
import ItemCard from '@/components/ItemCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useItemStatusStream } from '@/hooks/useItemStatusStream';
import { useItems, useInvalidateItems } from '@/hooks/useItems';

// Separate component that uses useSearchParams
function LibraryContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const {
    currentUser,
    token,
    updatePreferences,
    fetchTags,
    tags,
  } = useStore();
  
  // Initialize viewMode from user preferences or default to 'list'
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [fullUnreadCount, setFullUnreadCount] = useState<number | null>(null);
  const isInitialMount = useRef(true);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Debounce search query
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Fetch items with React Query's useInfiniteQuery
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch
  } = useItems({
    search: debouncedSearch,
    tags: selectedTags,
  });

  // Invalidate items cache for SSE updates
  const invalidateItems = useInvalidateItems();

  // Use SSE for real-time updates
  useItemStatusStream({
    onItemsUpdated: () => {
      invalidateItems();
      // Refetch to get updated items
      refetch();
    },
  });

  // Flatten all pages into a single array of items
  const allItems = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) => page.items);
  }, [data?.pages]);

  const displayItems = useMemo(() => {
    return allItems.map((item) => ({
      ...item,
      isRead: resolveItemReadState(item.id, item.isRead === true),
    }));
  }, [allItems]);

  // Get total count from the first page (all pages have the same total)
  const totalCount = useMemo(() => {
    return data?.pages?.[0]?.pagination?.total ?? null;
  }, [data?.pages]);

  const unreadCount = useMemo(() => {
    const paginationUnread = data?.pages?.[0]?.pagination?.unread;
    const loadedUnreadCount = displayItems.filter((item) => item.isRead !== true).length;
    if (fullUnreadCount !== null) {
      return fullUnreadCount;
    }
    if (typeof paginationUnread === 'number') {
      return Math.max(paginationUnread, loadedUnreadCount);
    }
    return loadedUnreadCount;
  }, [data?.pages, displayItems, fullUnreadCount]);

  // Sync local state with store preference on mount and when currentUser changes
  useEffect(() => {
    if (currentUser?.preferences?.viewMode) {
      setViewMode(currentUser.preferences.viewMode);
    }
  }, [currentUser]);

  // Initial fetch of tags on mount
  useEffect(() => {
    if (currentUser && isInitialMount.current) {
      isInitialMount.current = false;
      fetchTags();
    }
  }, [currentUser, fetchTags]);

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    updatePreferences({ viewMode: mode });
  };

  // Build an accurate unread count across the entire library (all pages),
  // independent of the currently displayed paginated subset.
  useEffect(() => {
    let isCancelled = false;

    const computeFullUnreadCount = async () => {
      if (!token) {
        setFullUnreadCount(null);
        return;
      }

      try {
        let cursor: string | undefined = undefined;
        let unread = 0;

        while (true) {
          const response = await getItems(token, undefined, undefined, 100, cursor);
          const items: RawSavedItem[] = Array.isArray(response) ? response : (response.items || []);

          for (const item of items) {
            const itemId = item.id;
            const serverIsRead = item.is_read === true;
            const effectiveIsRead = resolveItemReadState(itemId, serverIsRead);
            if (!effectiveIsRead) unread += 1;
          }

          if (Array.isArray(response)) {
            break;
          }

          if (!response.pagination?.has_more || !response.pagination?.next_cursor) {
            break;
          }

          cursor = response.pagination.next_cursor ?? undefined;
        }

        if (!isCancelled) {
          setFullUnreadCount(unread);
        }
      } catch (error) {
        if (!isCancelled) {
          // If the session expired, clear auth and avoid noisy console spam.
          // Other effects will redirect to /login once auth is cleared.
          if (isApiError(error) && (error.status === 401 || error.status === 403)) {
            useStore.getState().clearSession();
            return;
          }
          console.error('Failed to compute full unread count:', error);
          setFullUnreadCount(null);
        }
      }
    };

    computeFullUnreadCount();

    return () => {
      isCancelled = true;
    };
  }, [token, currentUser?.id]);

  // Get all unique tags for filter - use tags from store (with counts) or fallback to local computation
  const allTags = useMemo(() => {
    // If we have tags from the backend, use those (they're already sorted by frequency)
    if (tags && tags.length > 0) {
      return tags.map(t => t.name);
    }
    
    // Fallback to computing from items (for backwards compatibility)
    const tagSet = new Set<string>();
    allItems.forEach((item) => {
      item.tags.forEach((tag: string) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [allItems, tags]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting && hasNextPage && !isFetchingNextPage) {
          console.log('Loading next page...');
          fetchNextPage();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    const currentSentinel = sentinelRef.current;
    if (currentSentinel && hasNextPage) {
      observer.observe(currentSentinel);
    }

    return () => {
      if (currentSentinel) {
        observer.unobserve(currentSentinel);
      }
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header & Controls */}
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Library</h1>
            <p className="text-slate-400">
              {totalCount !== null
                ? `${totalCount} ${totalCount === 1 ? 'item' : 'items'} total (${unreadCount} unread)`
                : isLoading
                ? 'Loading...'
                : `${displayItems.length} ${displayItems.length === 1 ? 'item' : 'items'}`
              }
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Mobile Search (visible if needed, but we have global search) */}
            <div className="relative flex-1 md:w-64 md:flex-none">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <Input 
                placeholder="Filter library..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
              <Button 
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'} 
                size="icon" 
                className="h-8 w-8"
                onClick={() => handleViewModeChange('grid')}
              >
                <Grid className="w-4 h-4" />
              </Button>
              <Button 
                variant={viewMode === 'list' ? 'secondary' : 'ghost'} 
                size="icon" 
                className="h-8 w-8"
                onClick={() => handleViewModeChange('list')}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Tag Filters */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center">
            <Filter className="w-4 h-4 text-slate-500 mr-2" />
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-medium transition-all border",
                  selectedTags.includes(tag)
                    ? "bg-violet-600 border-violet-500 text-white shadow-lg shadow-violet-500/25"
                    : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10 hover:text-slate-200"
                )}
              >
                #{tag}
              </button>
            ))}
            {selectedTags.length > 0 && (
              <button 
                onClick={() => setSelectedTags([])}
                className="text-xs text-slate-500 hover:text-slate-300 ml-2 underline"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Grid/List View */}
        {displayItems.length > 0 ? (
          <>
            <div
              className={cn(
                "grid gap-6",
                viewMode === 'grid'
                  ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
                  : "grid-cols-1 gap-[15px]"
              )}
            >
              {displayItems.map((item) => (
                <ItemCard key={item.id} item={item} viewMode={viewMode} unreadVariant="accent" />
              ))}
            </div>
            
            {/* Loading indicator for infinite scroll */}
            {isFetchingNextPage && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-violet-500 animate-spin mr-2" />
                <span className="text-slate-400">Loading more items...</span>
              </div>
            )}
            
            {/* Sentinel for infinite scroll */}
            {hasNextPage && !isFetchingNextPage && (
              <div ref={sentinelRef} className="h-20 flex items-center justify-center">
                <div className="text-slate-500 text-sm">Scroll for more...</div>
              </div>
            )}
            
            {/* End of list indicator */}
            {!hasNextPage && displayItems.length > 0 && (
              <div className="flex items-center justify-center py-8">
                <div className="text-slate-500 text-sm">
                  {totalCount !== null 
                    ? `All ${totalCount} items loaded`
                    : 'No more items to load'
                  }
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6">
              <Search className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-300 mb-2">No items found</h3>
            <p className="text-slate-500 max-w-md">
              {searchQuery || selectedTags.length > 0 
                ? "Try adjusting your search or filters to find what you're looking for."
                : "Your library is empty. Start by saving some content!"}
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

// Main page component with Suspense boundary
export default function LibraryPage() {
  return (
    <Suspense fallback={
      <AppLayout>
        <div className="space-y-8">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-1">Library</h1>
              <p className="text-slate-400">Loading...</p>
            </div>
          </div>
          <div className="flex items-center justify-center py-20">
            <div className="animate-pulse text-slate-400">Loading your library...</div>
          </div>
        </div>
      </AppLayout>
    }>
      <LibraryContent />
    </Suspense>
  );
}

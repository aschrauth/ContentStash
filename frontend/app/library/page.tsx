"use client";

import React, { useState, useMemo, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Filter, Grid, List, Search, Loader2 } from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import AppLayout from '@/components/layout/AppLayout';
import ItemCard from '@/components/ItemCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useItemStatusStream } from '@/hooks/useItemStatusStream';
import { useItems, useInvalidateItems } from '@/hooks/useItems';
import { useVirtualizer } from '@tanstack/react-virtual';

// Separate component that uses useSearchParams
function LibraryContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const {
    currentUser,
    updatePreferences,
    fetchTags,
    tags,
  } = useStore();
  
  // Initialize viewMode from user preferences or default to 'list'
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [debouncedSearch, setDebouncedSearch] = useState(initialQuery);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const isInitialMount = useRef(true);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  // Debounce search query
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      // Reset pagination when search changes
      setCursor(undefined);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Reset pagination when tags change
  useEffect(() => {
    setCursor(undefined);
  }, [selectedTags]);

  // Fetch items with React Query
  const { data, isLoading, error, refetch } = useItems({
    search: debouncedSearch,
    tags: selectedTags,
    cursor,
  });

  // Invalidate items cache for SSE updates
  const invalidateItems = useInvalidateItems();

  // Use SSE for real-time updates
  useItemStatusStream({
    onItemsUpdated: invalidateItems,
  });

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

  // Filter items to show only non-archived items
  // Note: Backend already filters by owner_id, so we only need to filter out archived items
  const displayItems = useMemo(() => {
    const items = data?.items || [];
    return items.filter(item => !item.archivedAt);
  }, [data?.items]);

  // Get all unique tags for filter - use tags from store (with counts) or fallback to local computation
  const allTags = useMemo(() => {
    // If we have tags from the backend, use those (they're already sorted by frequency)
    if (tags && tags.length > 0) {
      return tags.map(t => t.name);
    }
    
    // Fallback to computing from items (for backwards compatibility)
    // Backend already filters by owner_id, so no need to filter again
    const items = data?.items || [];
    const tagSet = new Set<string>();
    items.forEach(item => {
      item.tags.forEach((tag: string) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [data?.items, tags]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  // Calculate items per row based on view mode
  const itemsPerRow = viewMode === 'grid' ? 3 : 1;
  const rowCount = Math.ceil(displayItems.length / itemsPerRow);

  // Set up virtualizer for rows
  const rowVirtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => (viewMode === 'grid' ? 350 : 200), // Estimated height per row
    overscan: 2, // Render 2 extra rows above and below viewport
  });

  // Load more items when scrolling near the end
  useEffect(() => {
    const [lastItem] = [...rowVirtualizer.getVirtualItems()].reverse();
    
    if (!lastItem) return;
    
    // If we're at the last row and there's more data, load it
    if (
      lastItem.index >= rowCount - 1 &&
      data?.pagination.has_more &&
      !isLoading &&
      data.pagination.next_cursor
    ) {
      setCursor(data.pagination.next_cursor);
    }
  }, [
    rowVirtualizer.getVirtualItems(),
    rowCount,
    data?.pagination.has_more,
    data?.pagination.next_cursor,
    isLoading,
  ]);

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header & Controls */}
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Library</h1>
            <p className="text-slate-400">
              {displayItems.length} {displayItems.length === 1 ? 'item' : 'items'} saved
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

        {/* Grid/List View with Virtual Scrolling */}
        {displayItems.length > 0 ? (
          <div
            ref={parentRef}
            className="h-[calc(100vh-280px)] overflow-auto"
            style={{ contain: 'strict' }}
          >
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const startIndex = virtualRow.index * itemsPerRow;
                const rowItems = displayItems.slice(startIndex, startIndex + itemsPerRow);
                
                return (
                  <div
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    ref={rowVirtualizer.measureElement}
                    className={cn(
                      "absolute top-0 left-0 w-full grid gap-6",
                      viewMode === 'grid'
                        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
                        : "grid-cols-1"
                    )}
                    style={{
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                  >
                    {rowItems.map((item) => (
                      <ItemCard key={item.id} item={item} viewMode={viewMode} />
                    ))}
                  </div>
                );
              })}
            </div>
            
            {/* Loading indicator for infinite scroll */}
            {isLoading && cursor && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-violet-500 animate-spin mr-2" />
                <span className="text-slate-400">Loading more items...</span>
              </div>
            )}
          </div>
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


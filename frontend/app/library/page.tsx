"use client";

import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Filter, Grid, List, Search, Tag } from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import AppLayout from '@/components/layout/AppLayout';
import ItemCard from '@/components/ItemCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export default function LibraryPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const { items, currentUser, updatePreferences } = useStore();
  
  // Initialize viewMode from user preferences or default to 'grid'
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Sync local state with store preference on mount and when currentUser changes
  useEffect(() => {
    if (currentUser?.preferences?.viewMode) {
      setViewMode(currentUser.preferences.viewMode);
    }
  }, [currentUser]);

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    updatePreferences({ viewMode: mode });
  };

  // Filter items based on search and tags
  const filteredItems = useMemo(() => {
    if (!currentUser) return [];
    
    let result = items.filter(item => item.ownerId === currentUser.id && !item.archivedAt);

    // Search Filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item => 
        item.title.toLowerCase().includes(query) || 
        item.description?.toLowerCase().includes(query) ||
        item.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Tag Filter
    if (selectedTags.length > 0) {
      result = result.filter(item => 
        selectedTags.every(tag => item.tags.includes(tag))
      );
    }

    // Sort by newest
    return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [items, currentUser, searchQuery, selectedTags]);

  // Get all unique tags for filter
  const allTags = useMemo(() => {
    if (!currentUser) return [];
    const tags = new Set<string>();
    items.filter(i => i.ownerId === currentUser.id).forEach(item => {
      item.tags.forEach(tag => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [items, currentUser]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header & Controls */}
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Library</h1>
            <p className="text-slate-400">
              {filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'} saved
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
        {filteredItems.length > 0 ? (
          <div className={cn(
            "grid gap-6",
            viewMode === 'grid' 
              ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" 
              : "grid-cols-1"
          )}>
            {filteredItems.map(item => (
              <ItemCard key={item.id} item={item} viewMode={viewMode} />
            ))}
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


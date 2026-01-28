"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, ExternalLink, Trash2, Clock, Tag, Edit3, Save, X, RefreshCw, Check, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';

import { useStore, SavedItem } from '@/lib/store';
import { formatDate, cn, cleanMarkdown } from '@/lib/utils';
import { API_ENDPOINTS } from '@/lib/api';
import AppLayout from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import RichTextEditor from '@/components/RichTextEditor';
import ConfirmationModal from '@/components/ConfirmationModal';

export default function ItemDetailPage() {
  // Unwrap params using React.use() if available, or fallback to direct access for older Next.js versions
  // In Next.js 15, params is a Promise. We need to handle it correctly.
  const params = useParams();
  const router = useRouter();
  const { items, updateItem, deleteItem, token, _hasHydrated } = useStore();
  const queryClient = useQueryClient();
  
  const [itemId, setItemId] = useState<string | null>(null);
  const [item, setItem] = useState<SavedItem | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [newTag, setNewTag] = useState('');
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Handle params safely
  useEffect(() => {
    if (params?.id) {
      setItemId(params.id as string);
    }
  }, [params]);

  // Load item data once itemId and items are available
  useEffect(() => {
    // Wait for Zustand hydration to complete
    if (!_hasHydrated) return;
    
    // Check both Zustand state and localStorage for token
    const storedToken = localStorage.getItem('token');
    if (!token && !storedToken) {
      router.push('/login');
      return;
    }
    
    if (!itemId) return;
    
    // ALWAYS fetch from API to get full item including archived_text
    // The list endpoint excludes archived_text for performance, so we need a fresh fetch
    const fetchItem = async () => {
      // Use stored token if Zustand token not yet available
      const authToken = token || localStorage.getItem('token');
      if (!authToken) {
        router.push('/login');
        return;
      }

      try {
        const response = await fetch(API_ENDPOINTS.itemById(itemId), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // Convert snake_case to camelCase
          const formattedItem = {
            id: data.id,
            ownerId: data.owner_id,
            url: data.url,
            title: data.title,
            description: data.description,
            imageUrl: data.image_url,
            faviconUrl: data.favicon_url,
            notesMarkdown: data.notes_markdown,
            tags: data.tags,
            suggestedTags: data.suggested_tags,
            suggestedTopic: data.suggested_topic,
            archivedText: data.archived_text,  // THIS IS THE KEY LINE
            extractionType: data.extraction_type,
            processingStatus: data.processing_status,
            createdAt: data.created_at,
            updatedAt: data.updated_at,
            archivedAt: data.archived_at
          };
          
          setItem(formattedItem);
          setEditTitle(formattedItem.title);
          setEditDescription(formattedItem.description || '');
          setNoteContent(formattedItem.notesMarkdown || '');
          setIsLoading(false);
          
        } else if (response.status === 404) {
          console.error('[Detail View] Item not found (404)');
          toast.error("Item not found");
          router.push('/library');
        } else {
          console.error('[Detail View] Failed to load item, status:', response.status);
          toast.error("Failed to load item");
          setIsLoading(false);
        }
      } catch (error) {
        console.error('[Detail View] Error fetching item:', error);
        toast.error("Failed to load item");
        setIsLoading(false);
      }
    };
    
    fetchItem();
  }, [itemId, token, router, _hasHydrated]);

  // Polling effect for pending items
  useEffect(() => {
    if (!itemId || !token || !item) return;
    
    // Only poll if status is pending, processing, or pending_local_extraction
    const shouldPoll = item.processingStatus === 'pending' ||
                       item.processingStatus === 'processing' ||
                       item.processingStatus === 'pending_local_extraction';
    
    if (!shouldPoll) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(API_ENDPOINTS.itemById(itemId), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const updatedData = await response.json();
          
          // Convert snake_case to camelCase
          const formattedItem: SavedItem = {
            id: updatedData.id,
            ownerId: updatedData.owner_id,
            url: updatedData.url,
            title: updatedData.title,
            description: updatedData.description,
            imageUrl: updatedData.image_url,
            faviconUrl: updatedData.favicon_url,
            notesMarkdown: updatedData.notes_markdown,
            tags: updatedData.tags,
            suggestedTags: updatedData.suggested_tags,
            suggestedTopic: updatedData.suggested_topic,
            archivedText: updatedData.archived_text,
            extractionType: updatedData.extraction_type,
            processingStatus: updatedData.processing_status,
            createdAt: updatedData.created_at,
            updatedAt: updatedData.updated_at,
            archivedAt: updatedData.archived_at
          };
          
          // Update both the Zustand store AND local state
          updateItem(itemId, updatedData);
          setItem(formattedItem);
          
          // If processing is complete, stop polling and show notification
          const isComplete = updatedData.processing_status === 'processed' ||
                            updatedData.processing_status === 'failed';
          
          if (isComplete) {
            clearInterval(pollInterval);
            
            if (updatedData.processing_status === 'processed') {
              toast.success('Content processed successfully!');
            } else if (updatedData.processing_status === 'failed') {
              toast.error('Processing failed: ' + (updatedData.processing_error || 'Unknown error'));
            }
          }
        }
      } catch (error) {
        console.error('Error polling item status:', error);
      }
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(pollInterval);
  }, [itemId, token, item?.processingStatus, updateItem]);

  // Autocomplete for tags
  useEffect(() => {
    const fetchAutocomplete = async (query: string) => {
      if (!token || query.length < 1) {
        setAutocompleteSuggestions([]);
        setShowAutocomplete(false);
        return;
      }

      try {
        const response = await fetch(API_ENDPOINTS.tagsAutocomplete(query), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const suggestions = await response.json();
          setAutocompleteSuggestions(suggestions);
          setShowAutocomplete(suggestions.length > 0);
        }
      } catch (error) {
        console.error('Failed to fetch autocomplete suggestions:', error);
      }
    };

    if (newTag && newTag.length > 0) {
      const query = newTag.startsWith('#') ? newTag.slice(1) : newTag;
      if (query.length > 0) {
        const timer = setTimeout(() => fetchAutocomplete(query), 300);
        return () => clearTimeout(timer);
      }
    }
    
    setShowAutocomplete(false);
  }, [newTag, token]);

  const selectAutocompleteTag = (tag: string) => {
    setNewTag(tag);
    setShowAutocomplete(false);
  };

  // Show loading while hydrating or loading item
  if (!_hasHydrated || isLoading || !item) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
        </div>
      </AppLayout>
    );
  }

  const handleSaveMetadata = () => {
    updateItem(item.id, {
      title: editTitle,
      description: editDescription,
    });
    setIsEditing(false);
    toast.success("Changes saved");
  };

  const handleSaveNotes = () => {
    updateItem(item.id, {
      notesMarkdown: noteContent,
    });
    toast.success("Notes saved");
  };

  const handleAddTag = (e: React.FormEvent) => {
    e.preventDefault();
    if (newTag.trim() && !item.tags.includes(newTag.trim())) {
      updateItem(item.id, {
        tags: [...item.tags, newTag.trim()]
      });
      setNewTag('');
      toast.success("Tag added");
    }
  };

  const removeTag = (tagToRemove: string) => {
    updateItem(item.id, {
      tags: item.tags.filter(tag => tag !== tagToRemove)
    });
  };

  const acceptSuggestion = (tag: string) => {
    if (!item.tags.includes(tag)) {
      updateItem(item.id, {
        tags: [...item.tags, tag],
        suggestedTags: item.suggestedTags?.filter(t => t !== tag)
      });
      toast.success(`Added #${tag}`);
    }
  };

  const handleDeleteClick = () => {
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    try {
      await deleteItem(item.id);
      
      // Invalidate React Query cache to refresh the library immediately
      queryClient.invalidateQueries({ queryKey: ['items'] });
      
      toast.success("Item deleted");
      router.push('/library');
    } catch (error) {
      console.error('Failed to delete item:', error);
      toast.error("Failed to delete item");
    }
  };

  const handleReprocess = async () => {
    if (!item.url || !token) return;
    setIsReprocessing(true);
    try {
      const response = await fetch(API_ENDPOINTS.itemReprocess(item.id), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const updatedItem = await response.json();
        updateItem(item.id, updatedItem);
        toast.success("Reprocessing started");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Reprocessing failed");
      }
    } catch (error) {
      console.error('Reprocess error:', error);
      toast.error("Reprocessing failed");
    } finally {
      setIsReprocessing(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto pb-20">
        {/* Back Button */}
        <button 
          onClick={() => router.back()}
          className="flex items-center text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Library
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Summary Panel - Header Section */}
            <div className="glass-panel p-8 rounded-2xl border border-white/10 relative overflow-hidden">
              {/* Background Image Blur */}
              {item.imageUrl && (
                <div className="absolute inset-0 z-0 opacity-10">
                  <img src={item.imageUrl} alt="" className="w-full h-full object-cover blur-xl" />
                </div>
              )}
              
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2">
                    {(item.processingStatus === 'pending' || item.processingStatus === 'processing') && (
                      <span className="px-2 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-medium border border-amber-500/30 flex items-center gap-1">
                        <RefreshCw className="w-3 h-3 animate-spin" /> Processing
                      </span>
                    )}
                    {item.processingStatus === 'pending_local_extraction' && (
                      <span className="px-2 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs font-medium border border-blue-500/30 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Pending Local Extraction
                      </span>
                    )}
                    {item.processingStatus === 'failed' && (
                      <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-300 text-xs font-medium border border-red-500/30 flex items-center gap-1">
                        <X className="w-3 h-3" /> Failed
                      </span>
                    )}
                    {item.processingStatus === 'processed' && (
                      <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-300 text-xs font-medium border border-green-500/30 flex items-center gap-1">
                        <Check className="w-3 h-3" /> Processed
                      </span>
                    )}
                    <span className="text-slate-400 text-xs flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {formatDate(item.createdAt)}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    {!isEditing ? (
                      <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                        <Edit3 className="w-4 h-4 mr-2" /> Edit
                      </Button>
                    ) : (
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                        <Button size="sm" onClick={handleSaveMetadata}>Save</Button>
                      </div>
                    )}
                  </div>
                </div>

                {isEditing ? (
                  <div className="space-y-4">
                    <Input 
                      value={editTitle} 
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="text-xl font-bold"
                    />
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-md p-3 text-slate-200 focus:ring-2 focus:ring-violet-500 outline-none"
                      rows={3}
                    />
                  </div>
                ) : (
                  <div className="clearfix">
                    <h1 className="text-3xl font-bold text-white mb-4 leading-tight">{item.title}</h1>
                    
                    {/* Preview Image - Floated Left */}
                    {item.imageUrl && (
                      <div className="float-left mr-6 mb-4 w-[250px] rounded-xl overflow-hidden border border-white/10 shadow-lg">
                        <img 
                          src={item.imageUrl} 
                          alt={item.title} 
                          className="w-full h-auto object-cover"
                        />
                      </div>
                    )}
                    
                    <p className="text-slate-300 text-lg leading-relaxed mb-6">{item.description}</p>
                  </div>
                )}

                {item.url && (
                  <div className="clear-both pt-4">
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-violet-400 hover:text-violet-300 transition-colors font-medium"
                    >
                      Visit Original Source <ExternalLink className="w-4 h-4 ml-2" />
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Personal Notes Panel */}
            <div className="glass-panel p-8 rounded-2xl border border-white/10">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Edit3 className="w-5 h-5 text-violet-400" /> Personal Notes
                </h2>
                <Button size="sm" variant="secondary" onClick={handleSaveNotes}>
                  <Save className="w-4 h-4 mr-2" /> Save Notes
                </Button>
              </div>
              
              <RichTextEditor
                value={noteContent}
                onChange={setNoteContent}
                placeholder="Write your thoughts here..."
              />
            </div>

            {/* Archived Content Panel */}
            {item.archivedText && (
              <div className="glass-panel p-8 rounded-2xl border border-white/10">
                <h2 className="text-xl font-bold text-white mb-4">Archived Content</h2>
                <div className="prose-archived max-w-none text-slate-300">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: (props) => <p {...props} />,
                      h1: (props) => <h1 {...props} />,
                      h2: (props) => <h2 {...props} />,
                      h3: (props) => <h3 {...props} />,
                      h4: (props) => <h4 {...props} />,
                      h5: (props) => <h5 {...props} />,
                      h6: (props) => <h6 {...props} />,
                      strong: (props) => <strong {...props} />,
                      em: (props) => <em {...props} />,
                      ul: (props) => <ul {...props} />,
                      ol: (props) => <ol {...props} />,
                      li: (props) => <li {...props} />,
                      a: (props) => <a {...props} />,
                      img: ({ src, alt, ...props }) => {
                        // Skip rendering images with empty src to avoid React warning
                        if (!src || (typeof src === 'string' && src.trim() === '')) {
                          return null;
                        }
                        return <img src={src} alt={alt} {...props} />;
                      },
                      code: ({ inline, ...props }: React.ComponentPropsWithoutRef<'code'> & { inline?: boolean }) =>
                        inline ? (
                          <code {...props} />
                        ) : (
                          <code {...props} />
                        ),
                      blockquote: (props) => <blockquote {...props} />,
                    }}
                  >
                    {cleanMarkdown(item.archivedText || '')}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Right Rail - Sidebar */}
          <div className="space-y-6">
            
            {/* Tags Panel */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Tag className="w-4 h-4 text-violet-400" /> Tags
              </h3>
              
              <div className="flex flex-wrap gap-2 mb-4">
                {item.tags.map(tag => (
                  <span
                    key={tag}
                    className="px-2 py-1 rounded-md bg-violet-600/20 text-violet-300 text-sm border border-violet-500/30 flex items-center gap-1 group"
                  >
                    #{tag}
                    <button
                      onClick={() => removeTag(tag)}
                      className="opacity-0 group-hover:opacity-100 hover:text-white transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>

              <form onSubmit={handleAddTag} className="relative">
                <Input
                  placeholder="Add tag..."
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  className="pr-8"
                />
                {showAutocomplete && autocompleteSuggestions.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-[#1e293b] border border-white/10 rounded-lg shadow-xl max-h-48 overflow-y-auto">
                    {autocompleteSuggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => selectAutocompleteTag(suggestion)}
                        className="w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-violet-600/20 hover:text-violet-300 transition-colors flex items-center gap-2"
                      >
                        <span className="text-violet-400">#</span>
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
                <button
                  type="submit"
                  className="absolute right-2 top-2.5 text-slate-400 hover:text-white"
                >
                  <Check className="w-4 h-4" />
                </button>
              </form>

              {/* AI Suggestions - moved inline with Tags */}
              {item.suggestedTags && item.suggestedTags.length > 0 && (
                <div className="mt-6 p-4 rounded-lg bg-gradient-to-br from-violet-900/20 to-transparent border border-violet-500/20">
                  <h4 className="font-semibold text-white mb-2 text-sm">AI Suggestions</h4>
                  <p className="text-xs text-slate-400 mb-3">Based on content analysis</p>
                  
                  <div className="flex flex-wrap gap-2">
                    {item.suggestedTags.map(tag => (
                      <button
                        key={tag}
                        onClick={() => acceptSuggestion(tag)}
                        className="px-2 py-1 rounded-md bg-white/5 hover:bg-violet-600/20 text-slate-300 hover:text-violet-300 text-xs border border-white/10 hover:border-violet-500/30 transition-all flex items-center gap-1"
                      >
                        + #{tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Extraction Type Panel */}
            {item.url && (
              <div className="glass-panel p-6 rounded-2xl border border-white/10">
                <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-violet-400" /> Extraction Type
                </h3>
                <div className="space-y-2">
                  <p className="text-xs text-slate-400 mb-3">
                    Current: <span className="text-violet-300 font-medium">
                      {item.extractionType === 'complete' ? 'Complete' : item.extractionType === 'local' ? 'Local' : 'Fast'}
                    </span>
                  </p>
                  <select
                    value={item.extractionType || 'fast'}
                    onChange={async (e) => {
                      const newType = e.target.value as 'fast' | 'complete' | 'local';
                      try {
                        // Update via Zustand store
                        await updateItem(item.id, { extractionType: newType });
                        
                        // Fetch the updated item from the API to get the new processing status
                        const response = await fetch(API_ENDPOINTS.itemById(item.id), {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                          },
                        });
                        
                        if (response.ok) {
                          const updatedData = await response.json();
                          
                          // Update local state with the fresh data from API including new processing status
                          const formattedItem: SavedItem = {
                            id: updatedData.id,
                            ownerId: updatedData.owner_id,
                            url: updatedData.url,
                            title: updatedData.title,
                            description: updatedData.description,
                            imageUrl: updatedData.image_url,
                            faviconUrl: updatedData.favicon_url,
                            notesMarkdown: updatedData.notes_markdown,
                            tags: updatedData.tags,
                            suggestedTags: updatedData.suggested_tags,
                            suggestedTopic: updatedData.suggested_topic,
                            archivedText: updatedData.archived_text,
                            extractionType: updatedData.extraction_type,
                            processingStatus: updatedData.processing_status,
                            createdAt: updatedData.created_at,
                            updatedAt: updatedData.updated_at,
                            archivedAt: updatedData.archived_at
                          };
                          
                          // This will trigger the polling effect to start monitoring
                          setItem(formattedItem);
                          toast.success(`Extraction type changed to ${newType}. Reprocessing...`);
                        } else {
                          toast.error('Failed to fetch updated item');
                        }
                      } catch (error) {
                        console.error('Error updating extraction type:', error);
                        toast.error('Failed to update extraction type');
                      }
                    }}
                    className="w-full bg-white/5 border border-white/10 rounded-md p-2 text-sm text-white focus:ring-2 focus:ring-violet-500 outline-none"
                  >
                    <option value="fast">Fast - Quick extraction</option>
                    <option value="complete">Complete - Full extraction with images</option>
                    <option value="local">Local - Browser extension extraction</option>
                  </select>
                  <p className="text-xs text-slate-500 mt-2">
                    {item.extractionType === 'local'
                      ? 'Local extraction requires the Chrome extension to process content'
                      : 'Changing this will automatically reprocess the content'}
                  </p>
                </div>
              </div>
            )}

            {/* Actions Panel */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-3">
              <h3 className="font-semibold text-white mb-2">Actions</h3>
              {(item.processingStatus === 'failed' || item.processingStatus === 'processed') && item.url && (
                <Button
                  variant="secondary"
                  className="w-full justify-start"
                  onClick={handleReprocess}
                  isLoading={isReprocessing}
                  disabled={isReprocessing}
                >
                  <RefreshCw className={cn("w-4 h-4 mr-2", isReprocessing && "animate-spin")} />
                  {isReprocessing ? 'Reprocessing...' : 'Reprocess Content'}
                </Button>
              )}
              <Button
                variant="destructive"
                className="w-full justify-start"
                onClick={handleDeleteClick}
              >
                <Trash2 className="w-4 h-4 mr-2" /> Delete Item
              </Button>
            </div>

            {/* Topic Panel */}
            {item.suggestedTopic && (
              <div className="glass-panel p-6 rounded-2xl border border-white/10">
                <h3 className="font-semibold text-white mb-2">Topic</h3>
                <span className="px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 text-sm border border-cyan-500/30 inline-block">
                  {item.suggestedTopic}
                </span>
              </div>
            )}

          </div>
        </div>
      </div>

      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Item"
        description="Are you sure you want to delete this item? This action cannot be undone immediately, but you can recover it from the archive within 30 days."
        confirmText="Delete"
        variant="danger"
      />
    </AppLayout>
  );
}


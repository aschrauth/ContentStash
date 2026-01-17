"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink, Trash2, Clock, Tag, Edit3, Save, X, RefreshCw, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import toast from 'react-hot-toast';

import { useStore } from '@/lib/store';
import { formatDate, cn } from '@/lib/utils';
import { simulateContentExtraction } from '@/lib/simulation';
import AppLayout from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import RichTextEditor from '@/components/RichTextEditor';

export default function ItemDetailPage() {
  // Unwrap params using React.use() if available, or fallback to direct access for older Next.js versions
  // In Next.js 15, params is a Promise. We need to handle it correctly.
  const params = useParams();
  const router = useRouter();
  const { items, updateItem, deleteItem, currentUser } = useStore();
  
  const [itemId, setItemId] = useState<string | null>(null);
  const [item, setItem] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [newTag, setNewTag] = useState('');
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Handle params safely
  useEffect(() => {
    if (params?.id) {
      setItemId(params.id as string);
    }
  }, [params]);

  // Load item data once itemId and items are available
  useEffect(() => {
    if (!itemId) return;
    
    // Wait for hydration
    if (items.length === 0 && typeof window !== 'undefined') {
       // If items are empty, it might be initial hydration. 
       // We'll wait a bit or let the store hydration finish.
    }

    const foundItem = items.find(i => i.id === itemId);
    
    if (foundItem) {
      setItem(foundItem);
      setEditTitle(foundItem.title);
      setEditDescription(foundItem.description || '');
      setNoteContent(foundItem.notesMarkdown || '');
      setIsLoading(false);
    } else if (items.length > 0) {
      // Only redirect if we have items but didn't find this one
      toast.error("Item not found");
      router.push('/library');
    } else {
      // Still loading or empty library
      // We'll keep loading state true for a moment
      const timer = setTimeout(() => {
         if (items.length === 0) setIsLoading(false); // Stop loading if still empty after timeout
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [items, itemId, router]);

  if (!currentUser) return null;
  
  if (isLoading || !item) {
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

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this item?")) {
      deleteItem(item.id);
      toast.success("Item deleted");
      router.push('/library');
    }
  };

  const handleReprocess = async () => {
    if (!item.url) return;
    setIsReprocessing(true);
    try {
      updateItem(item.id, { processingStatus: 'pending' });
      const result = await simulateContentExtraction(item.url);
      updateItem(item.id, {
        processingStatus: 'processed',
        archivedText: result.archivedText,
        suggestedTags: result.suggestedTags,
        suggestedTopic: result.suggestedTopic,
      });
      toast.success("Reprocessed successfully");
    } catch (error) {
      updateItem(item.id, { processingStatus: 'failed' });
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
            
            {/* Header Section */}
            <div className="glass-panel p-8 rounded-2xl border border-white/10 relative overflow-hidden">
              {/* Background Image Blur */}
              {item.imageUrl && (
                <div className="absolute inset-0 z-0 opacity-10">
                  <img src={item.imageUrl} className="w-full h-full object-cover blur-xl" />
                </div>
              )}
              
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2">
                    {item.processingStatus === 'pending' && (
                      <span className="px-2 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-medium border border-amber-500/30 flex items-center gap-1">
                        <RefreshCw className="w-3 h-3 animate-spin" /> Processing
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
                        <Button variant="primary" size="sm" onClick={handleSaveMetadata}>Save</Button>
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
                  <>
                    <h1 className="text-3xl font-bold text-white mb-4 leading-tight">{item.title}</h1>
                    <p className="text-slate-300 text-lg leading-relaxed mb-6">{item.description}</p>
                  </>
                )}

                {item.url && (
                  <a 
                    href={item.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-violet-400 hover:text-violet-300 transition-colors font-medium"
                  >
                    Visit Original Source <ExternalLink className="w-4 h-4 ml-2" />
                  </a>
                )}
              </div>
            </div>

            {/* Notes Section */}
            <div className="glass-panel p-8 rounded-2xl border border-white/10">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Edit3 className="w-5 h-5 text-violet-400" /> Personal Notes
                </h2>
                <Button size="sm" variant="secondary" onClick={handleSaveNotes}>
                  <Save className="w-4 h-4 mr-2" /> Save Notes
                </Button>
              </div>
              
              <div className="min-h-[300px]">
                <RichTextEditor 
                  value={noteContent} 
                  onChange={setNoteContent} 
                  placeholder="Write your thoughts here..."
                />
              </div>
            </div>

            {/* Archived Content Preview */}
            {item.archivedText && (
              <div className="glass-panel p-8 rounded-2xl border border-white/10">
                <h2 className="text-xl font-bold text-white mb-4">Archived Content</h2>
                <div className="prose prose-invert prose-sm max-w-none text-slate-400 line-clamp-[10]">
                  {item.archivedText}
                </div>
                <div className="mt-4 text-center">
                  <Button variant="ghost" size="sm">View Full Content</Button>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            
            {/* Actions */}
            <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-3">
              <h3 className="font-semibold text-white mb-2">Actions</h3>
              {item.processingStatus === 'failed' && (
                <Button 
                  variant="secondary" 
                  className="w-full justify-start" 
                  onClick={handleReprocess}
                  isLoading={isReprocessing}
                >
                  <RefreshCw className="w-4 h-4 mr-2" /> Reprocess Content
                </Button>
              )}
              <Button 
                variant="danger" 
                className="w-full justify-start"
                onClick={handleDelete}
              >
                <Trash2 className="w-4 h-4 mr-2" /> Delete Item
              </Button>
            </div>

            {/* Tags */}
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
                <button 
                  type="submit"
                  className="absolute right-2 top-2.5 text-slate-400 hover:text-white"
                >
                  <Check className="w-4 h-4" />
                </button>
              </form>
            </div>

            {/* Suggestions */}
            {item.suggestedTags && item.suggestedTags.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-gradient-to-br from-violet-900/20 to-transparent">
                <h3 className="font-semibold text-white mb-2">AI Suggestions</h3>
                <p className="text-xs text-slate-400 mb-4">Based on content analysis</p>
                
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

            {/* Topic */}
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
    </AppLayout>
  );
}


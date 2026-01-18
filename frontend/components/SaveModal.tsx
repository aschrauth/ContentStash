"use client";

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Link as LinkIcon, FileText, Loader2, Check, Sparkles } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import toast from 'react-hot-toast';

import { useStore } from '@/lib/store';
import { simulateMetadataFetch, simulateContentExtraction, simulateContentAnalysis } from '@/lib/simulation';
import { API_ENDPOINTS } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import RichTextEditor from '@/components/RichTextEditor';

const saveSchema = z.object({
  url: z.string().url().optional().or(z.literal('')),
  content: z.string().optional(),
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  tags: z.string().optional(), // Comma separated
}).refine(data => data.url || data.content, {
  message: "Either URL or Content is required",
  path: ["url"],
});

type SaveFormValues = z.infer<typeof saveSchema>;

interface SaveModalProps {
  onClose: () => void;
}

export default function SaveModal({ onClose }: SaveModalProps) {
  const addItem = useStore((state) => state.addItem);
  const updateItem = useStore((state) => state.updateItem);
  const token = useStore((state) => state.token);
  
  const [activeTab, setActiveTab] = useState<'url' | 'paste'>('url');
  const [isFetchingMeta, setIsFetchingMeta] = useState(false);
  const [hasFetchedMeta, setHasFetchedMeta] = useState(false);
  const [isGeneratingMeta, setIsGeneratingMeta] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [suggestedTags, setSuggestedTags] = useState<string[]>([]);
  const [suggestedTopic, setSuggestedTopic] = useState<string | null>(null);
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<SaveFormValues>({
    resolver: zodResolver(saveSchema),
    defaultValues: {
      title: '',
      description: '',
      tags: '',
      content: '',
    }
  });

  const urlValue = watch('url');
  const contentValue = watch('content');
  const currentTags = watch('tags') || '';

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

    // Check if user is typing a tag (after a comma or at the start)
    const tags = currentTags.split(',').map(t => t.trim());
    const lastTag = tags[tags.length - 1];
    
    // Only show autocomplete if the last tag starts with # or has some text
    if (lastTag && lastTag.length > 0) {
      const query = lastTag.startsWith('#') ? lastTag.slice(1) : lastTag;
      if (query.length > 0) {
        const timer = setTimeout(() => fetchAutocomplete(query), 300);
        return () => clearTimeout(timer);
      }
    }
    
    setShowAutocomplete(false);
  }, [currentTags, token]);

  const selectAutocompleteTag = (tag: string) => {
    const tags = currentTags.split(',').map(t => t.trim());
    tags[tags.length - 1] = tag;
    setValue('tags', tags.join(', '));
    setShowAutocomplete(false);
  };

  // Auto-fetch metadata when URL changes (debounced)
  useEffect(() => {
    if (!urlValue || activeTab !== 'url') {
      if (!urlValue && activeTab === 'url') {
        setHasFetchedMeta(false);
        setSuggestedTags([]);
        setSuggestedTopic(null);
      }
      return;
    }

    const timer = setTimeout(async () => {
      try {
        // Basic URL validation
        new URL(urlValue);
        
        setIsFetchingMeta(true);
        const meta = await simulateMetadataFetch(urlValue);
        setValue('title', meta.title);
        setValue('description', meta.description);
        setPreviewImage(meta.imageUrl);
        setSuggestedTags(meta.suggestedTags || []);
        setSuggestedTopic(meta.suggestedTopic || null);
        toast.success("Metadata fetched!");
        setHasFetchedMeta(true);
      } catch (e) {
        // Ignore invalid URLs during typing
      } finally {
        setIsFetchingMeta(false);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [urlValue, activeTab, setValue]);

  const handleGenerateMetadata = async () => {
    if (!contentValue || contentValue.trim().length < 10) {
      toast.error("Please enter some content first");
      return;
    }

    setIsGeneratingMeta(true);
    try {
      const analysis = await simulateContentAnalysis(contentValue);
      setValue('title', analysis.title);
      setValue('description', analysis.description);
      setValue('tags', analysis.tags.join(', '));
      toast.success("Metadata generated!");
      setHasFetchedMeta(true); // Reveal fields
    } catch (error) {
      toast.error("Failed to generate metadata");
    } finally {
      setIsGeneratingMeta(false);
    }
  };

  const addTag = (tag: string) => {
    const currentTagsList = currentTags.split(',').map(t => t.trim()).filter(Boolean);
    if (!currentTagsList.includes(tag)) {
      const newTags = [...currentTagsList, tag].join(', ');
      setValue('tags', newTags);
      // Remove from suggestions to give visual feedback
      setSuggestedTags(prev => prev.filter(t => t !== tag));
    }
  };

  const onSubmit = async (data: SaveFormValues) => {
    setIsSaving(true);
    try {
      const tags = data.tags 
        ? data.tags.split(',').map(t => t.trim().replace(/^#/, '')).filter(Boolean)
        : [];

      const newItemId = await addItem({
        title: data.title,
        description: data.description,
        url: activeTab === 'url' ? data.url : undefined,
        imageUrl: previewImage || undefined,
        tags,
        processingStatus: 'pending',
        archivedText: activeTab === 'paste' ? data.content : undefined,
        suggestedTopic: suggestedTopic || undefined,
      });

      toast.success("Item saved to library!");
      onClose();

      // Trigger background processing simulation
      if (activeTab === 'url' && data.url) {
        simulateContentExtraction(data.url)
          .then(result => {
            updateItem(newItemId, {
              processingStatus: 'processed',
              archivedText: result.archivedText,
              suggestedTags: result.suggestedTags,
              suggestedTopic: result.suggestedTopic,
            });
            toast.success("Content processed successfully!", { id: 'processing-success' });
          })
          .catch(() => {
            updateItem(newItemId, { processingStatus: 'failed' });
            toast.error("Content processing failed", { id: 'processing-fail' });
          });
      } else {
        // For pasted content, we just mark as processed immediately
        updateItem(newItemId, { processingStatus: 'processed' });
      }

    } catch (error) {
      toast.error("Failed to save item");
    } finally {
      setIsSaving(false);
    }
  };

  const showMetadataFields = activeTab === 'paste' || hasFetchedMeta;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-2xl bg-[#1e293b] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-white/5">
          <h2 className="text-xl font-bold text-white">Save to Stash</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          <button
            onClick={() => setActiveTab('url')}
            className={`flex-1 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
              activeTab === 'url' 
                ? 'bg-violet-600/10 text-violet-400 border-b-2 border-violet-500' 
                : 'text-slate-400 hover:bg-white/5'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            Save URL
          </button>
          <button
            onClick={() => setActiveTab('paste')}
            className={`flex-1 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
              activeTab === 'paste' 
                ? 'bg-violet-600/10 text-violet-400 border-b-2 border-violet-500' 
                : 'text-slate-400 hover:bg-white/5'
            }`}
          >
            <FileText className="w-4 h-4" />
            Paste Content
          </button>
        </div>

        {/* Form */}
        <div className="p-6 overflow-y-auto custom-scrollbar">
          <form id="save-form" onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            {activeTab === 'url' ? (
              <div className="space-y-2">
                <Label htmlFor="url">URL</Label>
                <div className="relative">
                  <Input 
                    id="url" 
                    placeholder="https://example.com/article" 
                    {...register('url')}
                    className="pr-10"
                  />
                  {isFetchingMeta && (
                    <div className="absolute right-3 top-2.5">
                      <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
                    </div>
                  )}
                </div>
                {errors.url && <p className="text-red-400 text-xs">{errors.url.message}</p>}
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="content">Content</Label>
                <Controller
                  name="content"
                  control={control}
                  render={({ field }) => (
                    <RichTextEditor
                      value={field.value || ''}
                      onChange={field.onChange}
                      placeholder="Paste formatted text here..."
                    />
                  )}
                />
                <div className="flex justify-end mt-2">
                  <Button 
                    type="button" 
                    variant="secondary" 
                    size="sm" 
                    onClick={handleGenerateMetadata}
                    isLoading={isGeneratingMeta}
                    disabled={!contentValue || contentValue.length < 10}
                    className="text-xs"
                  >
                    <Sparkles className="w-3 h-3 mr-2 text-amber-400" />
                    Generate Metadata
                  </Button>
                </div>
              </div>
            )}

            {showMetadataFields && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="space-y-6"
              >
                {/* Preview Card (Only for URL) */}
                {activeTab === 'url' && previewImage && (
                  <div className="relative h-40 w-full rounded-lg overflow-hidden border border-white/10">
                    <img src={previewImage} alt="Preview" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-4">
                      <p className="text-white font-medium text-sm truncate w-full">{watch('title')}</p>
                    </div>
                  </div>
                )}

                {/* AI Suggestions Panel */}
                {activeTab === 'url' && suggestedTags.length > 0 && (
                  <div className="glass-panel p-4 rounded-xl border border-white/10 bg-gradient-to-br from-violet-900/20 to-transparent">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <h3 className="font-semibold text-white text-sm">AI Suggestions</h3>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      {suggestedTags.map(tag => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => addTag(tag)}
                          className="px-2 py-1 rounded-md bg-white/5 hover:bg-violet-600/20 text-slate-300 hover:text-violet-300 text-xs border border-white/10 hover:border-violet-500/30 transition-all flex items-center gap-1"
                        >
                          + #{tag}
                        </button>
                      ))}
                    </div>
                    {suggestedTopic && (
                      <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-2">
                        <span className="text-xs text-slate-400">Topic:</span>
                        <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-xs border border-cyan-500/30">
                          {suggestedTopic}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-2 relative">
                  <Label htmlFor="tags">Tags (comma separated)</Label>
                  <Input
                    id="tags"
                    placeholder="design, research, ai"
                    {...register('tags')}
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
                  <p className="text-xs text-slate-500">
                    Tip: Start typing to see tag suggestions from your library.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input 
                    id="title" 
                    placeholder="Enter a title" 
                    {...register('title')}
                  />
                  {errors.title && <p className="text-red-400 text-xs">{errors.title.message}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description (Optional)</Label>
                  <textarea
                    id="description"
                    className="flex min-h-[80px] w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="Add a brief description..."
                    {...register('description')}
                  />
                </div>
              </motion.div>
            )}
          </form>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-white/10 bg-white/5 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" form="save-form" isLoading={isSaving} disabled={!showMetadataFields && activeTab === 'url'}>
            Save to Library
          </Button>
        </div>
      </motion.div>
    </div>
  );
}


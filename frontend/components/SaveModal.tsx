"use client";

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Link as LinkIcon, FileText, Loader2, Check } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import toast from 'react-hot-toast';

import { useStore } from '@/lib/store';
import { simulateMetadataFetch, simulateContentExtraction } from '@/lib/simulation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';

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
  
  const [activeTab, setActiveTab] = useState<'url' | 'paste'>('url');
  const [isFetchingMeta, setIsFetchingMeta] = useState(false);
  const [hasFetchedMeta, setHasFetchedMeta] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<SaveFormValues>({
    resolver: zodResolver(saveSchema),
    defaultValues: {
      title: '',
      description: '',
      tags: '',
    }
  });

  const urlValue = watch('url');

  // Auto-fetch metadata when URL changes (debounced)
  useEffect(() => {
    if (!urlValue || activeTab !== 'url') {
      if (!urlValue && activeTab === 'url') setHasFetchedMeta(false);
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
                <textarea
                  id="content"
                  className="flex min-h-[150px] w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="Paste text here..."
                  {...register('content')}
                />
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

                <div className="space-y-2">
                  <Label htmlFor="tags">Tags (comma separated)</Label>
                  <Input 
                    id="tags" 
                    placeholder="design, research, ai" 
                    {...register('tags')}
                  />
                  <p className="text-xs text-slate-500">
                    Tip: You can add more tags later.
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


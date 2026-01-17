"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ExternalLink, Hash, Clock, MoreHorizontal, FileText, Youtube, Image as ImageIcon, MessageSquare } from 'lucide-react';
import { SavedItem } from '@/lib/store';
import { formatDate, cn } from '@/lib/utils';

interface ItemCardProps {
  item: SavedItem;
}

export default function ItemCard({ item }: ItemCardProps) {
  const getIcon = () => {
    if (item.url?.includes('youtube') || item.url?.includes('youtu.be')) return <Youtube className="w-4 h-4" />;
    if (item.imageUrl && !item.url) return <ImageIcon className="w-4 h-4" />;
    if (item.url) return <ExternalLink className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  return (
    <Link href={`/items/${item.id}`}>
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ y: -4, transition: { duration: 0.2 } }}
        className="group relative h-full flex flex-col bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl overflow-hidden transition-all duration-300 shadow-lg hover:shadow-xl hover:shadow-violet-500/10"
      >
        {/* Image Preview */}
        {item.imageUrl && (
          <div className="relative h-40 w-full overflow-hidden bg-slate-900">
            <img 
              src={item.imageUrl} 
              alt={item.title} 
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 to-transparent opacity-60" />
            
            {/* Status Badge */}
            <div className="absolute top-3 right-3">
              {item.processingStatus === 'pending' && (
                <span className="px-2 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-medium border border-amber-500/30 backdrop-blur-md">
                  Processing
                </span>
              )}
              {item.processingStatus === 'failed' && (
                <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-300 text-xs font-medium border border-red-500/30 backdrop-blur-md">
                  Failed
                </span>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 p-5 flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              {getIcon()}
              <span>{formatDate(item.createdAt)}</span>
            </div>
          </div>

          {/* Title */}
          <h3 className="font-semibold text-lg leading-tight text-slate-100 mb-2 line-clamp-2 group-hover:text-violet-300 transition-colors">
            {item.title}
          </h3>

          {/* Description */}
          {item.description && (
            <p className="text-sm text-slate-400 line-clamp-3 mb-4 flex-1">
              {item.description}
            </p>
          )}

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 mt-auto pt-4">
            {item.tags.slice(0, 3).map(tag => (
              <span 
                key={tag} 
                className="px-2 py-0.5 rounded-md bg-white/5 text-slate-300 text-xs border border-white/5 group-hover:border-white/10 transition-colors"
              >
                #{tag}
              </span>
            ))}
            {item.tags.length > 3 && (
              <span className="px-2 py-0.5 rounded-md bg-white/5 text-slate-400 text-xs">
                +{item.tags.length - 3}
              </span>
            )}
          </div>
        </div>
      </motion.div>
    </Link>
  );
}


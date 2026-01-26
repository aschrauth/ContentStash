"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ExternalLink, FileText, Youtube, Image as ImageIcon } from 'lucide-react';
import { SavedItem } from '@/lib/store';
import { formatDate } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

/**
 * Performance optimizations:
 * - Removed `layout` prop to prevent expensive layout recalculations
 * - Added `will-change: transform` for GPU acceleration
 * - Disabled animations on mobile devices to improve performance
 * - Uses staggered children animation from parent for smoother rendering
 * - Uses tween transitions instead of spring for better performance
 */

interface ItemCardProps {
  item: SavedItem;
  viewMode?: 'grid' | 'list';
}

export default function ItemCard({ item, viewMode = 'grid' }: ItemCardProps) {
  const isMobile = useIsMobile();
  const getIcon = () => {
    if (item.url?.includes('youtube') || item.url?.includes('youtu.be')) return <Youtube className="w-4 h-4" />;
    if (item.imageUrl && !item.url) return <ImageIcon className="w-4 h-4" />;
    if (item.url) return <ExternalLink className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  if (viewMode === 'list') {
    // List view with compact horizontal layout on mobile
    return (
      <Link href={`/items/${item.id}`}>
        <motion.div
          variants={isMobile ? undefined : {
            hidden: { opacity: 0, y: 10 },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                type: "tween",
                duration: 0.3,
                ease: "easeOut"
              }
            }
          }}
          initial={isMobile ? undefined : "hidden"}
          animate={isMobile ? undefined : "visible"}
          whileHover={isMobile ? undefined : {
            scale: 1.01,
            transition: {
              type: "tween",
              duration: 0.2,
              ease: "easeOut"
            }
          }}
          style={isMobile ? undefined : { willChange: 'transform' }}
          className="group relative bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl overflow-hidden transition-all duration-300 shadow-sm hover:shadow-md"
        >
          {/* Mobile: Compact horizontal layout */}
          <div className="md:hidden">
            {/* Top section: Small thumbnail + Title/Date */}
            <div className="flex gap-3 p-3">
              {/* Small thumbnail on left (116x64) */}
              {item.imageUrl ? (
                <div className="relative w-[116px] h-16 flex-shrink-0 overflow-hidden bg-slate-900 rounded-lg">
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              ) : (
                <div className="w-[116px] h-16 flex-shrink-0 bg-white/5 flex items-center justify-center rounded-lg border border-white/5">
                  {getIcon()}
                </div>
              )}

              {/* Title and date stacked vertically */}
              <div className="flex-1 min-w-0 flex flex-col justify-center gap-1">
                <h3 className="font-semibold text-sm leading-tight text-slate-100 line-clamp-2 group-hover:text-violet-300 transition-colors">
                  {item.title}
                </h3>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span>{formatDate(item.createdAt)}</span>
                  {/* Status indicator */}
                  {item.processingStatus === 'pending' && (
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  )}
                  {item.processingStatus === 'failed' && (
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                  )}
                </div>
              </div>
            </div>

            {/* Bottom section: Description spanning full width (2 lines) */}
            {item.description && (
              <div className="px-3 pb-2">
                <p className="text-xs text-slate-400 line-clamp-2">
                  {item.description}
                </p>
              </div>
            )}

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5 px-3 pb-3">
              {item.tags.slice(0, 3).map(tag => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 rounded-md bg-white/5 text-slate-300 text-[10px] border border-white/5 group-hover:border-white/10 transition-colors"
                >
                  #{tag}
                </span>
              ))}
              {item.tags.length > 3 && (
                <span className="px-1.5 py-0.5 rounded-md bg-white/5 text-slate-400 text-[10px]">
                  +{item.tags.length - 3}
                </span>
              )}
            </div>
          </div>

          {/* Desktop: Horizontal layout with larger image */}
          <div className="hidden md:flex h-32">
            {/* Image Preview - Left Side Fixed Width */}
            {item.imageUrl ? (
              <div className="relative w-[230px] h-full flex-shrink-0 overflow-hidden bg-slate-900">
                <img
                  src={item.imageUrl}
                  alt={item.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/20" />
              </div>
            ) : (
              <div className="w-[230px] h-full flex-shrink-0 bg-white/5 flex items-center justify-center border-r border-white/5">
                {getIcon()}
              </div>
            )}

            {/* Content - Right Side */}
            <div className="flex-1 p-4 flex flex-col justify-between min-w-0">
              <div>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-2 mb-1">
                  <h3 className="font-semibold text-base text-slate-100 truncate group-hover:text-violet-300 transition-colors">
                    {item.title}
                  </h3>
                  <span className="text-xs text-slate-500 flex-shrink-0 flex items-center gap-1">
                    {formatDate(item.createdAt)}
                  </span>
                </div>
                
                <p className="text-sm text-slate-400 line-clamp-2 mb-2 opacity-100">
                  {item.description || "No description available."}
                </p>
              </div>

              <div className="flex items-center justify-between mt-auto">
                <div className="flex flex-wrap gap-1.5 overflow-hidden h-6">
                  {item.tags.slice(0, 4).map(tag => (
                    <span
                      key={tag}
                      className="px-1.5 py-0.5 rounded-md bg-white/5 text-slate-400 text-[10px] border border-white/5 group-hover:border-white/10 transition-colors whitespace-nowrap opacity-100"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
                
                {/* Status Badge (Mini) */}
                {item.processingStatus === 'pending' && (
                  <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" title="Processing" />
                )}
                {item.processingStatus === 'failed' && (
                  <div className="w-2 h-2 rounded-full bg-red-500" title="Failed" />
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </Link>
    );
  }

  // Grid View - Traditional vertical card layout (image on top, content below)
  return (
    <Link href={`/items/${item.id}`}>
      <motion.div
        variants={{
          hidden: { opacity: 0, scale: 0.95 },
          visible: {
            opacity: 1,
            scale: 1,
            transition: {
              type: "tween",
              duration: 0.3,
              ease: "easeOut"
            }
          }
        }}
        initial="hidden"
        animate="visible"
        whileHover={isMobile ? undefined : {
          y: -4,
          transition: {
            type: "tween",
            duration: 0.2,
            ease: "easeOut"
          }
        }}
        style={isMobile ? undefined : { willChange: 'transform' }}
        className="group relative h-full flex flex-col bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl overflow-hidden transition-all duration-300 shadow-lg hover:shadow-xl hover:shadow-violet-500/10"
      >
        {/* Image Preview - Top (all screen sizes) */}
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

        {/* Content - Bottom (all screen sizes) */}
        <div className="flex-1 p-5 flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              {getIcon()}
              <span>{formatDate(item.createdAt)}</span>
            </div>
            {/* Status indicator for items without images */}
            {!item.imageUrl && (
              <>
                {item.processingStatus === 'pending' && (
                  <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" title="Processing" />
                )}
                {item.processingStatus === 'failed' && (
                  <div className="w-2 h-2 rounded-full bg-red-500" title="Failed" />
                )}
              </>
            )}
          </div>

          {/* Title */}
          <h3 className="font-semibold text-lg leading-tight text-slate-100 mb-2 line-clamp-2 group-hover:text-violet-300 transition-colors opacity-100">
            {item.title}
          </h3>

          {/* Description */}
          {item.description && (
            <p className="text-sm text-slate-400 line-clamp-3 mb-4 flex-1 opacity-100">
              {item.description}
            </p>
          )}

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 mt-auto pt-4">
            {item.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-md bg-white/5 text-slate-300 text-xs border border-white/5 group-hover:border-white/10 transition-colors opacity-100"
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


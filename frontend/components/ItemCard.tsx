"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ExternalLink, FileText, Youtube, Image as ImageIcon, Clock } from 'lucide-react';
import { SavedItem } from '@/lib/store';
import { formatDate, cn, calculateReadTime } from '@/lib/utils'; // Added cn import

interface ItemCardProps {
  item: SavedItem;
  viewMode?: 'grid' | 'list';
  unreadVariant?: 'accent' | 'tinted';
}

export default function ItemCard({ item, viewMode = 'grid', unreadVariant = 'accent' }: ItemCardProps) {
  const isUnread = item.isRead !== true;

  const unreadCardClasses =
    unreadVariant === 'accent'
      ? isUnread
        ? "ring-1 ring-inset ring-sky-500/30"
        : ""
      : isUnread
      ? "bg-sky-500/10 hover:bg-sky-500/15 border-sky-500/30 hover:border-sky-400/40"
      : "";

  const getIcon = () => {
    if (item.url?.includes('youtube') || item.url?.includes('youtu.be')) return <Youtube className="w-4 h-4" />;
    if (item.imageUrl && !item.url) return <ImageIcon className="w-4 h-4" />;
    if (item.url) return <ExternalLink className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  if (viewMode === 'list') {
    return (
      <Link href={`/items/${item.id}`}>
        <motion.div
          variants={{
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
          initial="hidden"
          animate="visible"
          whileHover={{
            scale: 1.01,
            transition: { duration: 0.2, ease: "easeOut" }
          }}
          className={cn(
            "group relative bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl overflow-hidden transition-all duration-300 shadow-sm hover:shadow-md md:h-32",
            unreadCardClasses
          )}
          style={{ willChange: 'transform' }}
        >
          {isUnread && unreadVariant === 'accent' && (
            <span
              className="absolute left-0 top-0 bottom-0 w-1 bg-sky-400/90 z-30 pointer-events-none"
              aria-hidden="true"
            />
          )}
          {/* Unified Container: Flex Wrap on Mobile, Flex Row No Wrap on Desktop */}
          <div className="flex flex-wrap md:flex-nowrap items-start md:items-stretch h-full">

            {/* Image Section */}
            {/* Mobile: Small left thumbnail (116px width). Desktop: Fixed left sidebar (230px width) */}
            <div className={`
              relative shrink-0 overflow-hidden bg-slate-900 
              
              /* Mobile Styles */
              w-[116px] h-16 m-3 rounded-lg 
 
              /* Desktop Styles */
              md:w-[230px] md:h-full md:m-0 md:rounded-none
            `}>
              {item.imageUrl ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    loading="lazy"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  {/* Desktop Overlay */}
                  <div className="hidden md:block absolute inset-0 bg-gradient-to-r from-transparent to-black/20" />
                </>
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-white/5 border border-white/5 md:border-r md:border-y-0 md:border-l-0">
                  {getIcon()}
                </div>
              )}
            </div>

            {/* Content Wrapper */}
            {/* Mobile: display:contents allows children to participate in the parent flex-wrap container
                Desktop: flex-col to stack vertically in the right pane */}
            <div className="contents md:flex md:flex-col md:flex-1 md:justify-between md:min-w-0 md:p-4">

              {/* Title & Metadata Block (Right of thumbnail on mobile) */}
              <div className="flex flex-col justify-center gap-1 w-[calc(100%-116px-24px)] pt-3 pr-3 md:w-full md:h-auto md:p-0 md:mb-1">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-sm md:text-base leading-tight text-slate-100 line-clamp-2 truncate group-hover:text-violet-300 transition-colors md:flex-1">
                    {item.title}
                  </h3>

                  {/* Status Indicators */}
                  <div className="flex-shrink-0 flex items-center mt-1">
                    {item.processingStatus === 'pending' && (
                      <div className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-amber-500 animate-pulse" title="Processing" />
                    )}
                    {item.processingStatus === 'failed' && (
                      <div className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-red-500" title="Failed" />
                    )}
                  </div>
                </div>

                {/* Metadata: Read Time, Date and Source - Integrated into right column on Mobile */}
                <div className="flex flex-col md:flex-row md:items-center gap-1 md:gap-2 text-[11px] md:text-xs text-slate-500 mt-1 md:mt-0">
                  <div className="flex items-center gap-2">
                    {/* Read Time */}
                    {calculateReadTime(item.wordCount) && (
                      <span className="text-slate-400 font-medium flex items-center gap-1 shrink-0">
                        <Clock className="w-3 h-3" />
                        {calculateReadTime(item.wordCount)}
                      </span>
                    )}

                    {calculateReadTime(item.wordCount) && <span className="text-slate-600">•</span>}

                    {/* Date */}
                    <span className="text-slate-400 shrink-0">
                      {formatDate(item.createdAt)}
                    </span>

                    {item.source && <span className="hidden md:inline text-slate-600 md:ml-1">•</span>}
                  </div>

                  {/* Source (Stacked on Mobile, Row on Desktop) */}
                  {item.source && (
                    <span className="truncate text-slate-500 max-w-[200px] md:max-w-none">
                      {item.source}
                    </span>
                  )}
                </div>
              </div>

              {/* Description Section (Mobile: Stacks below image/title row) */}
              <div className="w-full px-3 pb-2 md:p-0 md:mb-2 order-3 md:order-none">
                <p className="text-xs md:text-sm text-slate-400 line-clamp-2 opacity-100">
                  {item.description || "No description available."}
                </p>
              </div>

              {/* Tags Section - Only show if tags exist to avoid extra space */}
              {item.tags.length > 0 && (
                <div className="w-full px-3 pb-3 md:p-0 md:mt-auto order-4 md:order-none">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-wrap gap-1.5 overflow-hidden h-5 md:h-6">
                      {item.tags.slice(0, 3).map(tag => (
                        <span
                          key={tag}
                          className="px-1.5 py-0.5 rounded-md bg-white/5 text-slate-300 text-[10px] border border-white/5 group-hover:border-white/10 transition-colors whitespace-nowrap"
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
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </Link>
    );
  }

  // Grid View - Traditional vertical card layout
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
        whileHover={{
          y: -4,
          transition: { type: "tween", duration: 0.2, ease: "easeOut" }
        }}
        className={cn(
          "group relative h-full flex flex-col bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl overflow-hidden transition-all duration-300 shadow-lg hover:shadow-xl hover:shadow-violet-500/10",
          unreadCardClasses
        )}
        style={{ willChange: 'transform' }}
      >
        {isUnread && unreadVariant === 'accent' && (
          <span
            className="absolute left-0 top-0 bottom-0 w-1 bg-sky-400/90 z-30 pointer-events-none"
            aria-hidden="true"
          />
        )}
        {/* Image Preview */}
        {item.imageUrl && (
          <div className="relative h-40 w-full overflow-hidden bg-slate-900">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.imageUrl}
              alt={item.title}
              loading="lazy"
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

        {/* Content */}
        <div className="relative flex-1 p-5 flex flex-col">
          {/* Header */}
          <div className="flex flex-col gap-2 mb-3">
            {/* Metadata Part 1: Icon, Read Time, Date */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                {getIcon()}
                {calculateReadTime(item.wordCount) && (
                  <>
                    <span className="text-slate-400 font-medium flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {calculateReadTime(item.wordCount)}
                    </span>
                    <span>•</span>
                  </>
                )}
                <span>{formatDate(item.createdAt)}</span>
              </div>

              {/* Status Indicator (for items without images) */}
              {!item.imageUrl && (
                <div className="flex items-center gap-1">
                  {item.processingStatus === 'pending' && (
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" title="Processing" />
                  )}
                  {item.processingStatus === 'failed' && (
                    <div className="w-2 h-2 rounded-full bg-red-500" title="Failed" />
                  )}
                </div>
              )}
            </div>

            {/* Metadata Part 2: Source (New Line) */}
            {item.source && (
              <div className="text-xs text-slate-500 truncate mt-0.5">
                {item.source}
              </div>
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

"use client";

import React, { useRef } from 'react';
import { Bold, Italic, List, ListOrdered, Link as LinkIcon, Quote, Code, Heading1, Heading2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function MarkdownEditor({ value, onChange, placeholder, className }: MarkdownEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const insertFormat = (prefix: string, suffix: string = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);

    const newText = text.substring(0, start) + prefix + selectedText + suffix + text.substring(end);
    
    onChange(newText);

    // Restore focus and selection
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, end + prefix.length);
    }, 0);
  };

  const ToolbarButton = ({ icon: Icon, onClick, title }: { icon: any, onClick: () => void, title: string }) => (
    <button
      type="button"
      onClick={onClick}
      className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
      title={title}
    >
      <Icon className="w-4 h-4" />
    </button>
  );

  return (
    <div className={cn("flex flex-col border border-white/10 rounded-lg overflow-hidden bg-white/5 focus-within:ring-2 focus-within:ring-violet-500/50 transition-all", className)}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border-b border-white/10 bg-white/5">
        <ToolbarButton icon={Bold} onClick={() => insertFormat('**', '**')} title="Bold" />
        <ToolbarButton icon={Italic} onClick={() => insertFormat('*', '*')} title="Italic" />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton icon={Heading1} onClick={() => insertFormat('# ')} title="Heading 1" />
        <ToolbarButton icon={Heading2} onClick={() => insertFormat('## ')} title="Heading 2" />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton icon={List} onClick={() => insertFormat('- ')} title="Bullet List" />
        <ToolbarButton icon={ListOrdered} onClick={() => insertFormat('1. ')} title="Numbered List" />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton icon={Quote} onClick={() => insertFormat('> ')} title="Quote" />
        <ToolbarButton icon={Code} onClick={() => insertFormat('`', '`')} title="Inline Code" />
        <ToolbarButton icon={LinkIcon} onClick={() => insertFormat('[', '](url)')} title="Link" />
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 w-full bg-transparent border-none p-4 text-slate-200 placeholder:text-slate-500 focus:outline-none resize-none font-mono text-sm min-h-[300px]"
      />
    </div>
  );
}


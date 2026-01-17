"use client";

import React, { useEffect, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import { marked } from 'marked';
import TurndownService from 'turndown';
import { 
  Bold, 
  Italic, 
  List, 
  ListOrdered, 
  Quote, 
  Code, 
  Heading1, 
  Heading2, 
  Undo, 
  Redo,
  Link as LinkIcon
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced'
});

export default function RichTextEditor({ value, onChange, placeholder, className }: RichTextEditorProps) {
  const [isMounted, setIsMounted] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-violet-400 underline cursor-pointer',
        },
      }),
    ],
    editorProps: {
      attributes: {
        // Removed 'prose' class to rely on our custom global styles for better control
        class: 'focus:outline-none min-h-[300px] p-4 text-slate-200',
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      const markdown = turndownService.turndown(html);
      onChange(markdown);
    },
    immediatelyRender: false,
  });

  // Handle initial value loading
  useEffect(() => {
    if (editor && value && !isMounted) {
      const parseMarkdown = async () => {
        const html = await marked.parse(value);
        editor.commands.setContent(html);
        setIsMounted(true);
      };
      parseMarkdown();
    }
  }, [editor, value, isMounted]);

  if (!editor) {
    return <div className="h-[300px] bg-white/5 rounded-lg animate-pulse border border-white/10" />;
  }

  const ToolbarButton = ({ onClick, isActive = false, icon: Icon, title }: any) => (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "p-2 rounded-md transition-colors",
        isActive 
          ? "bg-violet-600 text-white" 
          : "text-slate-400 hover:text-white hover:bg-white/10"
      )}
      title={title}
    >
      <Icon className="w-4 h-4" />
    </button>
  );

  return (
    <div className={cn("flex flex-col border border-white/10 rounded-lg overflow-hidden bg-white/5", className)}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border-b border-white/10 bg-white/5">
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBold().run()} 
          isActive={editor.isActive('bold')} 
          icon={Bold} 
          title="Bold" 
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleItalic().run()} 
          isActive={editor.isActive('italic')} 
          icon={Italic} 
          title="Italic" 
        />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} 
          isActive={editor.isActive('heading', { level: 1 })} 
          icon={Heading1} 
          title="Heading 1" 
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} 
          isActive={editor.isActive('heading', { level: 2 })} 
          icon={Heading2} 
          title="Heading 2" 
        />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBulletList().run()} 
          isActive={editor.isActive('bulletList')} 
          icon={List} 
          title="Bullet List" 
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleOrderedList().run()} 
          isActive={editor.isActive('orderedList')} 
          icon={ListOrdered} 
          title="Numbered List" 
        />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBlockquote().run()} 
          isActive={editor.isActive('blockquote')} 
          icon={Quote} 
          title="Quote" 
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleCodeBlock().run()} 
          isActive={editor.isActive('codeBlock')} 
          icon={Code} 
          title="Code Block" 
        />
        <div className="w-px h-4 bg-white/10 mx-1" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().undo().run()} 
          icon={Undo} 
          title="Undo" 
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().redo().run()} 
          icon={Redo} 
          title="Redo" 
        />
      </div>

      {/* Editor Content */}
      <EditorContent editor={editor} />
    </div>
  );
}


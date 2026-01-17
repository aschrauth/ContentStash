"use client";

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

// Dynamic import to avoid SSR issues with Quill
const ReactQuill = dynamic(() => import('react-quill'), {
  ssr: false,
  loading: () => <div className="h-64 flex items-center justify-center bg-white/5 rounded-lg"><Loader2 className="w-6 h-6 animate-spin text-violet-400" /></div>,
});

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function RichTextEditor({ value, onChange, placeholder }: RichTextEditorProps) {
  // Custom toolbar options
  const modules = {
    toolbar: [
      [{ 'header': [1, 2, 3, false] }],
      ['bold', 'italic', 'underline', 'strike'],
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      ['link', 'blockquote', 'code-block'],
      ['clean']
    ],
  };

  const formats = [
    'header',
    'bold', 'italic', 'underline', 'strike',
    'list', 'bullet',
    'link', 'blockquote', 'code-block'
  ];

  return (
    <div className="rich-text-editor-wrapper">
      <link rel="stylesheet" href="https://unpkg.com/react-quill@1.3.3/dist/quill.snow.css" />
      <style jsx global>{`
        .rich-text-editor-wrapper .ql-toolbar {
          background: rgba(255, 255, 255, 0.05);
          border-color: rgba(255, 255, 255, 0.1);
          border-top-left-radius: 0.5rem;
          border-top-right-radius: 0.5rem;
        }
        .rich-text-editor-wrapper .ql-container {
          background: rgba(255, 255, 255, 0.02);
          border-color: rgba(255, 255, 255, 0.1);
          border-bottom-left-radius: 0.5rem;
          border-bottom-right-radius: 0.5rem;
          font-size: 1rem;
          color: #e2e8f0;
          min-height: 300px;
        }
        .rich-text-editor-wrapper .ql-stroke {
          stroke: #94a3b8 !important;
        }
        .rich-text-editor-wrapper .ql-fill {
          fill: #94a3b8 !important;
        }
        .rich-text-editor-wrapper .ql-picker {
          color: #94a3b8 !important;
        }
        .rich-text-editor-wrapper .ql-editor.ql-blank::before {
          color: #64748b;
          font-style: normal;
        }
      `}</style>
      <ReactQuill
        theme="snow"
        value={value}
        onChange={onChange}
        modules={modules}
        formats={formats}
        placeholder={placeholder}
      />
    </div>
  );
}


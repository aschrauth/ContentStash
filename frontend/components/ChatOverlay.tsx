"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, MessageSquare, Sparkles, ExternalLink } from 'lucide-react';
import { useStore } from '@/lib/store';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChatOverlay({ isOpen, onClose }: ChatOverlayProps) {
  const { currentUser, createChatThread, sendChatMessage, chatThreads, fetchChatThread } = useStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize or get active thread
  useEffect(() => {
    if (isOpen && !activeThreadId) {
      // Find most recent thread or create new one if none exists? 
      // For MVP, let's just start fresh or show history list.
      // Let's auto-create a thread if none exists for simplicity in this view
      if (chatThreads.length > 0) {
        setActiveThreadId(chatThreads[0].id);
      }
    }
  }, [isOpen, chatThreads, activeThreadId]);

  const activeThread = chatThreads.find(t => t.id === activeThreadId);
  const messages = React.useMemo(() => activeThread?.messages || [], [activeThread]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentUser) return;

    const userMessage = input;
    setInput('');
    setIsTyping(true);

    try {
      let threadId = activeThreadId;
      
      if (!threadId) {
        // Create new thread with first message
        threadId = await createChatThread(userMessage);
        setActiveThreadId(threadId);
      } else {
        // Send message to existing thread
        await sendChatMessage(threadId, userMessage);
      }
      
      // Fetch updated thread to get the latest messages
      await fetchChatThread(threadId);
    } catch (error) {
      console.error('Error sending message:', error);
      // Optionally show error to user
    } finally {
      setIsTyping(false);
    }
  };

  const handleNewChat = () => {
    setActiveThreadId(null);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />

          {/* Chat Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full md:w-[500px] bg-[#0f172a] border-l border-white/10 shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-slate-900/50 backdrop-blur-md">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-violet-600 to-cyan-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-white">Ask Stash</h2>
                  <p className="text-xs text-slate-400">AI-powered search</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={handleNewChat}>
                  New Chat
                </Button>
                <Button variant="ghost" size="icon" onClick={onClose}>
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-50">
                  <MessageSquare className="w-12 h-12 mb-4 text-violet-400" />
                  <h3 className="text-lg font-medium text-white mb-2">Ask anything</h3>
                  <p className="text-sm text-slate-400">
                    &quot;What did I save about UX design?&quot;<br/>
                    &quot;Summarize my notes on React&quot;<br/>
                    &quot;Find articles about AI&quot;
                  </p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      "flex flex-col max-w-[90%]",
                      msg.role === 'user' ? "ml-auto items-end" : "mr-auto items-start"
                    )}
                  >
                    <div
                      className={cn(
                        "p-4 rounded-2xl text-sm leading-relaxed",
                        msg.role === 'user'
                          ? "bg-violet-600 text-white rounded-tr-none"
                          : "bg-white/10 text-slate-200 rounded-tl-none border border-white/5"
                      )}
                    >
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          className="prose prose-invert prose-sm max-w-none"
                          components={{
                            // Customize markdown rendering
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                            li: ({ children }) => <li className="ml-2">{children}</li>,
                            strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
                            em: ({ children }) => <em className="italic">{children}</em>,
                            code: ({ children }) => <code className="bg-black/30 px-1.5 py-0.5 rounded text-violet-300">{children}</code>,
                            pre: ({ children }) => <pre className="bg-black/30 p-3 rounded-lg overflow-x-auto mb-2">{children}</pre>,
                            a: ({ href, children }) => (
                              <a href={href} className="text-violet-300 hover:text-violet-200 underline" target="_blank" rel="noopener noreferrer">
                                {children}
                              </a>
                            ),
                            h1: ({ children }) => <h1 className="text-xl font-bold mb-2 text-white">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-lg font-bold mb-2 text-white">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-base font-bold mb-2 text-white">{children}</h3>,
                            blockquote: ({ children }) => (
                              <blockquote className="border-l-4 border-violet-500 pl-4 italic my-2 text-slate-300">
                                {children}
                              </blockquote>
                            ),
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      )}
                    </div>

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 space-y-2 w-full">
                        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider ml-1">Sources</p>
                        {msg.citations.map((citation, idx) => (
                          <Link
                            key={idx}
                            href={`/items/${citation.id}`}
                            onClick={onClose}
                            className="block p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-violet-500/30 transition-all group"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <h4 className="text-xs font-semibold text-violet-300 line-clamp-1 group-hover:text-violet-200">
                                {citation.title}
                              </h4>
                              <ExternalLink className="w-3 h-3 text-slate-500 group-hover:text-violet-400" />
                            </div>
                            <p className="text-xs text-slate-400 mt-1 line-clamp-2 italic">
                              &quot;{citation.excerpt}&quot;
                            </p>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
              
              {isTyping && (
                <div className="flex items-center gap-2 text-slate-500 text-sm ml-2">
                  <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                  <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-white/10 bg-slate-900/50 backdrop-blur-md">
              <form onSubmit={handleSend} className="relative">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about your library..."
                  className="pr-12 py-6 bg-white/5 border-white/10 focus:bg-white/10"
                  disabled={isTyping}
                />
                <Button
                  type="submit"
                  size="icon"
                  className="absolute right-2 top-2 h-8 w-8 bg-violet-600 hover:bg-violet-500"
                  disabled={!input.trim() || isTyping}
                >
                  <Send className="w-4 h-4" />
                </Button>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


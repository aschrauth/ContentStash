"use client";

import React, { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Navbar from './Navbar';
import { AnimatePresence } from 'framer-motion';
import SaveModal from '@/components/SaveModal';
import ChatOverlay from '@/components/ChatOverlay';

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated } = useAuth(true);
  const pathname = usePathname();
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const resetDocumentInteractivity = () => {
    if (typeof document === 'undefined') return;

    const { body, documentElement } = document;

    body.style.overflow = '';
    body.style.pointerEvents = '';
    documentElement.style.overflow = '';
    documentElement.style.pointerEvents = '';
    body.removeAttribute('data-scroll-locked');
    documentElement.removeAttribute('data-scroll-locked');
  };

  useEffect(() => {
    setIsSaveModalOpen(false);
    setIsChatOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (isSaveModalOpen || isChatOpen) return;

    resetDocumentInteractivity();

    return () => {
      resetDocumentInteractivity();
    };
  }, [isSaveModalOpen, isChatOpen, pathname]);

  if (!isAuthenticated) {
    // Show a loading shell instead of blocking blank screen
    return (
      <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col">
        <Navbar onSaveClick={() => { }} onChatClick={() => { }} />
        <main className="flex-1 container mx-auto px-4 py-8">
          <div className="space-y-8 animate-pulse opacity-50">
            <div className="h-8 w-48 bg-slate-800 rounded mb-4"></div>
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="h-64 bg-slate-800 rounded-xl"></div>
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col">
      {/* Background Ambient Effects - Visible only on larger screens for mobile performance */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 hidden sm:block">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-violet-900/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan-900/10 rounded-full blur-[120px]" />
      </div>

      <Navbar
        onSaveClick={() => setIsSaveModalOpen(true)}
        onChatClick={() => setIsChatOpen(true)}
      />

      <main className="flex-1 container mx-auto px-2 md:px-4 py-4 md:py-8 relative z-10">
        {children}
      </main>

      <AnimatePresence>
        {isSaveModalOpen && (
          <SaveModal onClose={() => setIsSaveModalOpen(false)} />
        )}
      </AnimatePresence>

      <ChatOverlay isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}

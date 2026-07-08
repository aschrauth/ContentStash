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
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <Navbar onSaveClick={() => { }} onChatClick={() => { }} />
        <main className="flex-1 container mx-auto px-4 py-8">
          <div className="space-y-8 animate-pulse opacity-50">
            <div className="h-8 w-48 bg-muted rounded mb-4"></div>
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="h-64 bg-card border border-border rounded-xl"></div>
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_58%_48%_at_0%_0%,oklch(88%_0.075_166_/_0.46),transparent_72%),linear-gradient(180deg,oklch(99%_0.006_83_/_0.72),transparent_58%)]" />
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

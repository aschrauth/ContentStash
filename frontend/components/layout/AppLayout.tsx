"use client";

import React, { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import Navbar from './Navbar';
import { motion, AnimatePresence } from 'framer-motion';
import SaveModal from '@/components/SaveModal';
import ChatOverlay from '@/components/ChatOverlay';

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { isAuthenticated } = useAuth(true);
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  if (!isAuthenticated) {
    return null; // or loading spinner, but useAuth handles redirect
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col">
      {/* Background Ambient Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-violet-900/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan-900/10 rounded-full blur-[120px]" />
      </div>

      <Navbar 
        onSaveClick={() => setIsSaveModalOpen(true)} 
        onChatClick={() => setIsChatOpen(true)}
      />

      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
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


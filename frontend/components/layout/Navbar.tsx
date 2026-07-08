"use client";

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, LogOut, MessageSquare } from 'lucide-react';
import { useStore } from '@/lib/store';
import { Button } from '@/components/ui/Button';

interface NavbarProps {
  onSaveClick: () => void;
  onChatClick: () => void;
}

export default function Navbar({ onSaveClick, onChatClick }: NavbarProps) {
  const router = useRouter();
  const { currentUser, logout } = useStore();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-card/90 backdrop-blur-xl">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/library" className="flex items-center gap-2 font-bold text-xl tracking-tight">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/stash-mark.svg"
            alt="ContentStash"
            className="h-9 w-9 rounded-[10px] shadow-[0_8px_24px_oklch(24%_0.03_75_/_0.09)]"
          />
          <span className="hidden text-foreground sm:inline-block">
            Stash
          </span>
        </Link>

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          <Button
            onClick={onSaveClick}
            className="hidden sm:flex"
            size="sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            Save
          </Button>

          <Button
            onClick={onSaveClick}
            className="sm:hidden"
            size="icon"
          >
            <Plus className="w-5 h-5" />
          </Button>

          <Button
            onClick={onChatClick}
            variant="secondary"
            size="sm"
            className="hidden sm:flex"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Ask Stash
          </Button>

          <Button
            onClick={onChatClick}
            variant="secondary"
            size="icon"
            className="sm:hidden"
          >
            <MessageSquare className="w-5 h-5" />
          </Button>

          {/* User Menu (Simplified for MVP) */}
          <div className="flex items-center gap-2 border-l border-border pl-4 ml-2">
            <div className="hidden md:block text-right mr-2">
              <div className="text-sm font-medium text-foreground">{currentUser?.name}</div>
              <div className="text-xs text-muted-foreground truncate max-w-[100px]">{currentUser?.email}</div>
            </div>

            <Button variant="ghost" size="icon" onClick={handleLogout} title="Logout">
              <LogOut className="w-5 h-5 text-muted-foreground hover:text-red-600 transition-colors" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

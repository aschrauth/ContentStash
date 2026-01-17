"use client";

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';

export function useAuth(requireAuth = true) {
  const router = useRouter();
  const pathname = usePathname();
  const currentUser = useStore((state) => state.currentUser);

  useEffect(() => {
    if (requireAuth && !currentUser) {
      router.push('/login');
    } else if (!requireAuth && currentUser && (pathname === '/login' || pathname === '/register')) {
      router.push('/library');
    }
  }, [currentUser, requireAuth, router, pathname]);

  return { currentUser, isAuthenticated: !!currentUser };
}


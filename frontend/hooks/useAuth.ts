"use client";

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { API_ENDPOINTS } from '@/lib/api';

export function useAuth(requireAuth = true) {
  const router = useRouter();
  const pathname = usePathname();
  const currentUser = useStore((state) => state.currentUser);
  const token = useStore((state) => state.token);

  useEffect(() => {
    // If we have a token but no user, fetch the user profile
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');
      
      if (storedToken && !currentUser) {
        try {
          const response = await fetch(API_ENDPOINTS.me, {
            headers: {
              'Authorization': `Bearer ${storedToken}`,
            },
          });

          if (response.ok) {
            const user = await response.json();
            useStore.setState({ currentUser: user, token: storedToken });
            
            // Fetch items after successful authentication
            const fetchItems = useStore.getState().fetchItems;
            await fetchItems();
          } else {
            // Token is invalid, clear it
            localStorage.removeItem('token');
            useStore.setState({ currentUser: null, token: null });
          }
        } catch (error) {
          console.error('Failed to fetch user profile:', error);
          localStorage.removeItem('token');
          useStore.setState({ currentUser: null, token: null });
        }
      }
    };

    initAuth();
  }, [currentUser]);

  useEffect(() => {
    if (requireAuth && !currentUser && !localStorage.getItem('token')) {
      router.push('/login');
    } else if (!requireAuth && currentUser && (pathname === '/login' || pathname === '/register')) {
      router.push('/library');
    }
  }, [currentUser, requireAuth, router, pathname]);

  return { currentUser, isAuthenticated: !!currentUser };
}

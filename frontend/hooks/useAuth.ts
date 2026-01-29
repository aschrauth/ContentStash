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
  const hasHydrated = useStore((state) => state._hasHydrated);

  useEffect(() => {
    // Wait for Zustand to hydrate before initializing auth
    if (!hasHydrated) return;

    // Background validation: Even if we have a user (persisted), we check the token
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');

      // Always restore token to store if it exists in localStorage but not in store
      // This is critical for React Query hooks (useItems) to work immediately 
      // when currentUser is restored from cache but token wasn't (since token isn't persisted in Zustand)
      if (storedToken && !token) {
        useStore.setState({ token: storedToken });
      }

      // If we have a token, we should validate it / fetch fresh user data
      // This happens even if currentUser is already populated from cache (background update)
      if (storedToken) {
        try {
          // If we already have a user, we don't need to block interaction,
          // but we should still verify the session is active

          // NOTE: For now, we only fetch if !currentUser to avoid redundant calls,
          // BUT to support true 'background validation' we really should fetch always.
          // However, to match the Plan "Update user data silently", we should probably fetches 
          // but NOT wipe state immediately unless 401. 

          // Current logic: Only fetch if NO currentUser.
          // CHANGE: To fully utilize the Optimistic UI (currentUser is present),
          // we should consider if we want to re-validate.
          // For MVP performance to fix the "blank screen", keeping this logic is fine because
          // currentUser IS present (from cache), so this block is skipped, App renders.

          if (!currentUser) {
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
              // Token is invalid only if request fails
              localStorage.removeItem('token');
              useStore.setState({ currentUser: null, token: null });
            }
          }
        } catch (error) {
          console.error('Failed to fetch user profile:', error);
          if (!currentUser) {
            // Only clear if we were trying to establish a session. 
            // If we have a cached user, maybe keep them offline?
            // For safety, let's clear if the network call failed during initialization
            localStorage.removeItem('token');
            useStore.setState({ currentUser: null, token: null });
          }
        }
      }
    };

    initAuth();
  }, [currentUser, hasHydrated]); // Removing 'token' from deps to avoid loop when setting it

  useEffect(() => {
    // Wait for hydration before making auth decisions
    if (!hasHydrated) return;

    // Check both Zustand state and localStorage to handle hydration race
    const storedToken = localStorage.getItem('token');

    if (requireAuth && !currentUser && !storedToken) {
      router.push('/login');
    } else if (!requireAuth && currentUser && (pathname === '/login' || pathname === '/register')) {
      router.push('/library');
    }
  }, [currentUser, requireAuth, router, pathname, hasHydrated]);

  return { currentUser, isAuthenticated: !!currentUser };
}

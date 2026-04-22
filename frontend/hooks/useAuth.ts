"use client";

import { useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { API_ENDPOINTS } from '@/lib/api';
import { isJwtExpired } from '@/lib/authToken';

export function useAuth(requireAuth = true) {
  const router = useRouter();
  const pathname = usePathname();
  const currentUser = useStore((state) => state.currentUser);
  const token = useStore((state) => state.token);
  const hasHydrated = useStore((state) => state._hasHydrated);
  const currentUserRef = useRef(currentUser);
  const tokenRef = useRef(token);

  useEffect(() => {
    currentUserRef.current = currentUser;
    tokenRef.current = token;
  }, [currentUser, token]);

  useEffect(() => {
    // Wait for Zustand to hydrate before initializing auth
    if (!hasHydrated) return;

    // Background validation: Even if we have a user (persisted), we check the token
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');

      // Always restore token to store if it exists in localStorage but not in store
      // This is critical for React Query hooks (useItems) to work immediately 
      // when currentUser is restored from cache but token wasn't (since token isn't persisted in Zustand)
      if (storedToken && !tokenRef.current) {
        useStore.setState({ token: storedToken });
      }

      // If we have a token, we should validate it / fetch fresh user data
      // This happens even if currentUser is already populated from cache (background update)
      if (storedToken) {
        if (isJwtExpired(storedToken)) {
          useStore.getState().clearSession();
          return;
        }

        try {
          // Always validate the stored token, even if currentUser is restored from cache.
          // Otherwise an expired token can linger and cause 401 spam across the app.
          const response = await fetch(API_ENDPOINTS.me, {
            headers: {
              'Authorization': `Bearer ${storedToken}`,
            },
          });

          if (response.ok) {
            const user = await response.json();
            const state = useStore.getState();
            const existingUser = state.currentUser;
            const shouldUpdateUser =
              !existingUser ||
              existingUser.id !== user.id ||
              existingUser.email !== user.email ||
              existingUser.name !== user.name ||
              state.token !== storedToken;

            if (shouldUpdateUser) {
              useStore.setState({ currentUser: user, token: storedToken });
            }

            // Fetch items after successful authentication
            await useStore.getState().fetchItems();
          } else if (response.status === 401 || response.status === 403) {
            useStore.getState().clearSession();
          } else if (!currentUserRef.current) {
            // Non-auth failure when trying to establish a session: be conservative.
            useStore.getState().clearSession();
          }
        } catch (error) {
          console.error('Failed to fetch user profile:', error);
          if (!currentUserRef.current) {
            // Only clear if we were trying to establish a session. 
            // If we have a cached user, maybe keep them offline?
            // For safety, let's clear if the network call failed during initialization
            useStore.getState().clearSession();
          }
        }
      }
    };

    initAuth();
  }, [hasHydrated]); // Run once after hydration; avoid auth revalidation loops on currentUser updates.

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

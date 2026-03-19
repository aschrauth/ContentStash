"use client";

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { API_ENDPOINTS, getItems, isApiError, normalizeSavedItem, RawSavedItem } from './api';
import { getQueryClient } from '@/components/providers/QueryProvider';

// --- Types ---

export type User = {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  preferences?: {
    viewMode?: 'grid' | 'list';
  };
};

export type SavedItem = {
  id: string;
  ownerId: string;
  url?: string;
  title: string;
  description?: string;
  imageUrl?: string;
  faviconUrl?: string;
  notesMarkdown?: string;
  tags: string[];
  suggestedTags?: string[];
  suggestedTopic?: string;
  aiSummary?: string;
  archivedText?: string;
  source?: string;
  wordCount?: number;
  extractionType?: 'fast' | 'complete' | 'local';
  processingStatus: 'pending' | 'processing' | 'processed' | 'failed' | 'pending_local_extraction';
  isRead?: boolean;
  createdAt: string;
  updatedAt: string;
};

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  citations?: {
    id: string;
    excerpt: string;
    title: string;
  }[];
  createdAt: string;
};

export type ChatThread = {
  id: string;
  ownerId: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

export type TagWithCount = {
  name: string;
  count: number;
};

// --- Store ---

interface AppState {
  currentUser: User | null;
  token: string | null;
  clearSession: () => void;
  items: SavedItem[];
  tags: TagWithCount[];
  chatThreads: ChatThread[];
  _hasHydrated: boolean;
  setHasHydrated: (state: boolean) => void;

  // Pagination state
  itemsCursor: string | null;
  hasMoreItems: boolean;
  isLoadingMore: boolean;

  // Actions
  register: (email: string, password: string, name: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (name: string, email: string) => void;
  updatePreferences: (preferences: Partial<User['preferences']>) => void;

  fetchItems: (searchQuery?: string, tags?: string[], loadMore?: boolean) => Promise<void>;
  loadMoreItems: () => Promise<void>;
  fetchTags: () => Promise<void>;
  addItem: (item: Omit<SavedItem, 'id' | 'createdAt' | 'updatedAt' | 'ownerId'>) => Promise<string>;
  updateItem: (id: string, updates: Partial<SavedItem>) => Promise<void>;
  deleteItem: (id: string) => Promise<void>;

  fetchChatThreads: () => Promise<void>;
  fetchChatThread: (threadId: string) => Promise<ChatThread | null>;
  createChatThread: (firstMessage: string) => Promise<string>;
  sendChatMessage: (threadId: string, message: string) => Promise<void>;
  deleteChatThread: (id: string) => Promise<void>;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      currentUser: null,
      token: null,
      clearSession: () => {
        const queryClient = getQueryClient();
        if (queryClient) {
          queryClient.clear();
        }

        localStorage.removeItem('token');
        set({
          currentUser: null,
          token: null,
          items: [],
          chatThreads: [],
          tags: []
        });
      },
      items: [],
      tags: [],
      chatThreads: [],
      _hasHydrated: false,
      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },

      // Pagination state
      itemsCursor: null,
      hasMoreItems: false,
      isLoadingMore: false,

      register: async (email, password, name) => {
        try {
          // Clear React Query cache before registering new user
          const queryClient = getQueryClient();
          if (queryClient) {
            queryClient.clear();
          }

          // Clear Zustand persisted state (items and chatThreads)
          set({ items: [], chatThreads: [] });

          const response = await fetch(API_ENDPOINTS.signup, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password, name }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
          }

          const data = await response.json();

          // Store token in localStorage
          localStorage.setItem('token', data.token);

          set({
            currentUser: data.user,
            token: data.token
          });

          // Let useAuth hook handle initial data fetch
        } catch (error) {
          console.error('Registration error:', error);
          throw error;
        }
      },

      login: async (email, password) => {
        try {
          // Clear React Query cache before logging in new user
          const queryClient = getQueryClient();
          if (queryClient) {
            queryClient.clear();
          }

          // Clear Zustand persisted state (items and chatThreads)
          set({ items: [], chatThreads: [] });

          const response = await fetch(API_ENDPOINTS.login, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
          }

          const data = await response.json();

          // Store token in localStorage
          localStorage.setItem('token', data.token);

          set({
            currentUser: data.user,
            token: data.token
          });

          // Let useAuth hook handle initial data fetch
        } catch (error) {
          console.error('Login error:', error);
          throw error;
        }
      },

      logout: () => {
        // Clear React Query cache FIRST to prevent stale data
        const queryClient = getQueryClient();
        if (queryClient) {
          queryClient.clear();
        }

        // Remove token from localStorage
        localStorage.removeItem('token');

        // Call logout endpoint (optional, mainly for server-side cleanup)
        const { token } = get();
        if (token) {
          fetch(API_ENDPOINTS.logout, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }).catch(() => {
            // Ignore network/auth errors during logout cleanup.
          });
        }

        // Clear all user-specific state including persisted data
        set({
          currentUser: null,
          token: null,
          items: [],
          chatThreads: [],
          tags: []
        });
      },

      updateProfile: (name, email) => {
        const { currentUser } = get();
        if (!currentUser) return;

        const updatedUser = { ...currentUser, name, email };
        set({ currentUser: updatedUser });
      },

      updatePreferences: (preferences) => {
        const { currentUser } = get();
        if (!currentUser) return;

        const updatedUser = {
          ...currentUser,
          preferences: { ...currentUser.preferences, ...preferences }
        };

        set({ currentUser: updatedUser });
      },

      fetchItems: async (searchQuery?: string, tags?: string[], loadMore: boolean = false) => {
        const { token, itemsCursor, items: currentItems } = get();
        if (!token) return;

        try {
          // Use cursor if loading more, otherwise start fresh
          const cursor = loadMore ? itemsCursor : undefined;

          // If not loading more, reset pagination state
          if (!loadMore) {
            set({ itemsCursor: null, hasMoreItems: false });
          }

          const response = await getItems(token, searchQuery, tags, 50, cursor ?? undefined);

          // Handle both old format (array) and new format (object with pagination)
          let itemsData: RawSavedItem[];
          let pagination: { next_cursor: string | null; has_more: boolean } | null = null;

          if (Array.isArray(response)) {
            // Old format - backward compatibility
            itemsData = response;
          } else {
            // New format with pagination
            itemsData = response.items;
            pagination = response.pagination;
          }

          // Convert snake_case to camelCase for all items
          const formattedItems: SavedItem[] = itemsData.map(normalizeSavedItem);

          // If loading more, append to existing items; otherwise replace
          const newItems = loadMore ? [...currentItems, ...formattedItems] : formattedItems;

          set({
            items: newItems,
            itemsCursor: pagination?.next_cursor || null,
            hasMoreItems: pagination?.has_more || false
          });
        } catch (error) {
          if (isApiError(error) && (error.status === 401 || error.status === 403)) {
            get().clearSession();
            return;
          }
          console.error('Failed to fetch items:', error);
          // On error, ensure we're not stuck in loading state
          if (loadMore) {
            set({ isLoadingMore: false });
          }
        }
      },

      loadMoreItems: async () => {
        const { itemsCursor, isLoadingMore, hasMoreItems } = get();
        if (isLoadingMore || !hasMoreItems || !itemsCursor) return;

        set({ isLoadingMore: true });
        await get().fetchItems('', [], true); // loadMore = true
        set({ isLoadingMore: false });
      },

      fetchTags: async () => {
        const { token } = get();
        if (!token) return;

        try {
          const response = await fetch(API_ENDPOINTS.tags, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
              get().clearSession();
              return;
            }
            throw new Error('Failed to fetch tags');
          }

          const tagsData = await response.json();
          set({ tags: tagsData });
        } catch (error) {
          console.error('Failed to fetch tags:', error);
        }
      },

      addItem: async (itemData) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.items, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              url: itemData.url,
              title: itemData.title,
              description: itemData.description,
              image_url: itemData.imageUrl,  // Convert camelCase to snake_case
              favicon_url: itemData.faviconUrl,  // Convert camelCase to snake_case
              notes_markdown: itemData.notesMarkdown,  // Convert camelCase to snake_case
              tags: itemData.tags,
              archived_text: itemData.archivedText,  // Convert camelCase to snake_case
              source: itemData.source,
              extraction_type: itemData.extractionType,  // Convert camelCase to snake_case
              is_read: itemData.isRead ?? false,
            }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create item');
          }

          const newItem = await response.json();

          // Convert snake_case to camelCase for frontend
          const formattedItem: SavedItem = {
            id: newItem.id,
            ownerId: newItem.owner_id,
            url: newItem.url,
            title: newItem.title,
            description: newItem.description,
            imageUrl: newItem.image_url,
            faviconUrl: newItem.favicon_url,
            notesMarkdown: newItem.notes_markdown,
            tags: newItem.tags || [],
            suggestedTags: newItem.suggested_tags,
            suggestedTopic: newItem.suggested_topic,
            archivedText: newItem.archived_text,
            source: newItem.source,
            wordCount: newItem.word_count,
            extractionType: newItem.extraction_type as 'fast' | 'complete' | 'local' | undefined,
            processingStatus: newItem.processing_status,
            isRead: newItem.is_read === true,
            createdAt: newItem.created_at,
            updatedAt: newItem.updated_at,
          };

          // Add to local state
          const { items } = get();
          set({ items: [formattedItem, ...items] });

          return formattedItem.id;
        } catch (error) {
          console.error('Failed to create item:', error);
          throw error;
        }
      },

      updateItem: async (id, updates) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.itemById(id), {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              url: updates.url,
              title: updates.title,
              description: updates.description,
              image_url: updates.imageUrl,
              favicon_url: updates.faviconUrl,
              notes_markdown: updates.notesMarkdown,
              tags: updates.tags,
              archived_text: updates.archivedText,
              source: updates.source,
              extraction_type: updates.extractionType,
              is_read: updates.isRead,
            }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update item');
          }

          const updatedItem = await response.json();

          // Convert snake_case to camelCase
          const formattedItem: SavedItem = {
            id: updatedItem.id,
            ownerId: updatedItem.owner_id,
            url: updatedItem.url,
            title: updatedItem.title,
            description: updatedItem.description,
            imageUrl: updatedItem.image_url,
            faviconUrl: updatedItem.favicon_url,
            notesMarkdown: updatedItem.notes_markdown,
            tags: updatedItem.tags || [],
            suggestedTags: updatedItem.suggested_tags,
            suggestedTopic: updatedItem.suggested_topic,
            aiSummary: updatedItem.ai_summary,
            archivedText: updatedItem.archived_text,
            source: updatedItem.source,
            wordCount: updatedItem.word_count,
            extractionType: updatedItem.extraction_type as 'fast' | 'complete' | 'local' | undefined,
            processingStatus: updatedItem.processing_status,
            isRead: updatedItem.is_read === true,
            createdAt: updatedItem.created_at,
            updatedAt: updatedItem.updated_at,
          };

          // Update local state
          const { items } = get();
          set({
            items: items.map(item =>
              item.id === id ? formattedItem : item
            )
          });
        } catch (error) {
          console.error('Failed to update item:', error);
          throw error;
        }
      },

      deleteItem: async (id) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.itemById(id), {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete item');
          }

          // Remove from local state after successful hard delete.
          const { items } = get();
          set({
            items: items.filter(item => item.id !== id)
          });
        } catch (error) {
          console.error('Failed to delete item:', error);
          throw error;
        }
      },

      fetchChatThreads: async () => {
        const { token } = get();
        if (!token) return;

        try {
          const response = await fetch(API_ENDPOINTS.chatThreads, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch chat threads');
          }

          const threadsData = await response.json();

          // Convert snake_case to camelCase
          const formattedThreads: ChatThread[] = threadsData.map((thread: Record<string, unknown>) => ({
            id: thread.id as string,
            ownerId: thread.owner_id as string,
            title: thread.title as string,
            messages: (thread.messages as Record<string, unknown>[])?.map((msg: Record<string, unknown>) => ({
              role: msg.role as 'user' | 'assistant',
              content: msg.content as string,
              citations: (msg.citations as Record<string, unknown>[])?.map((cit: Record<string, unknown>) => ({
                id: cit.id as string,
                title: cit.title as string,
                excerpt: cit.excerpt as string,
              })) || [],
              createdAt: msg.created_at as string,
            })) || [],
            createdAt: thread.created_at as string,
            updatedAt: thread.updated_at as string,
          }));

          set({ chatThreads: formattedThreads });
        } catch (error) {
          console.error('Failed to fetch chat threads:', error);
        }
      },

      fetchChatThread: async (threadId: string) => {
        const { token } = get();
        if (!token) return null;

        try {
          const response = await fetch(API_ENDPOINTS.chatThreadById(threadId), {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch chat thread');
          }

          const threadData = await response.json();

          // Convert snake_case to camelCase
          const formattedThread: ChatThread = {
            id: threadData.id as string,
            ownerId: threadData.owner_id as string,
            title: threadData.title as string,
            messages: (threadData.messages as Record<string, unknown>[])?.map((msg: Record<string, unknown>) => ({
              role: msg.role as 'user' | 'assistant',
              content: msg.content as string,
              citations: (msg.citations as Record<string, unknown>[])?.map((cit: Record<string, unknown>) => ({
                id: cit.id as string,
                title: cit.title as string,
                excerpt: cit.excerpt as string,
              })) || [],
              createdAt: msg.created_at as string,
            })) || [],
            createdAt: threadData.created_at as string,
            updatedAt: threadData.updated_at as string,
          };

          // Update local state
          const { chatThreads } = get();
          const existingIndex = chatThreads.findIndex(t => t.id === threadId);
          if (existingIndex >= 0) {
            const updatedThreads = [...chatThreads];
            updatedThreads[existingIndex] = formattedThread;
            set({ chatThreads: updatedThreads });
          } else {
            set({ chatThreads: [formattedThread, ...chatThreads] });
          }

          return formattedThread;
        } catch (error) {
          console.error('Failed to fetch chat thread:', error);
          return null;
        }
      },

      createChatThread: async (firstMessage: string) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.chatThreads, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ message: firstMessage }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create chat thread');
          }

          const threadData = await response.json();

          // Convert snake_case to camelCase
          const formattedThread: ChatThread = {
            id: threadData.id as string,
            ownerId: threadData.owner_id as string,
            title: threadData.title as string,
            messages: (threadData.messages as Record<string, unknown>[])?.map((msg: Record<string, unknown>) => ({
              role: msg.role as 'user' | 'assistant',
              content: msg.content as string,
              citations: (msg.citations as Record<string, unknown>[])?.map((cit: Record<string, unknown>) => ({
                id: cit.id as string,
                title: cit.title as string,
                excerpt: cit.excerpt as string,
              })) || [],
              createdAt: msg.created_at as string,
            })) || [],
            createdAt: threadData.created_at as string,
            updatedAt: threadData.updated_at as string,
          };

          // Add to local state
          const { chatThreads } = get();
          set({ chatThreads: [formattedThread, ...chatThreads] });

          return formattedThread.id;
        } catch (error) {
          console.error('Failed to create chat thread:', error);
          throw error;
        }
      },

      sendChatMessage: async (threadId: string, message: string) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.chatThreadMessages(threadId), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ message }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send message');
          }

          const threadData = await response.json();

          // Convert snake_case to camelCase
          const formattedThread: ChatThread = {
            id: threadData.id as string,
            ownerId: threadData.owner_id as string,
            title: threadData.title as string,
            messages: (threadData.messages as Record<string, unknown>[])?.map((msg: Record<string, unknown>) => ({
              role: msg.role as 'user' | 'assistant',
              content: msg.content as string,
              citations: (msg.citations as Record<string, unknown>[])?.map((cit: Record<string, unknown>) => ({
                id: cit.id as string,
                title: cit.title as string,
                excerpt: cit.excerpt as string,
              })) || [],
              createdAt: msg.created_at as string,
            })) || [],
            createdAt: threadData.created_at as string,
            updatedAt: threadData.updated_at as string,
          };

          // Update local state
          const { chatThreads } = get();
          set({
            chatThreads: chatThreads.map(thread =>
              thread.id === threadId ? formattedThread : thread
            )
          });
        } catch (error) {
          console.error('Failed to send message:', error);
          throw error;
        }
      },

      deleteChatThread: async (id: string) => {
        const { token } = get();
        if (!token) throw new Error("Not authenticated");

        try {
          const response = await fetch(API_ENDPOINTS.chatThreadById(id), {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete thread');
          }

          // Remove from local state
          const { chatThreads } = get();
          set({ chatThreads: chatThreads.filter(t => t.id !== id) });
        } catch (error) {
          console.error('Failed to delete thread:', error);
          throw error;
        }
      },
    }),
    {
      name: 'stash-storage-v2', // Bump version to invalidate old bloated cache
      partialize: (state) => ({
        currentUser: state.currentUser,
        // Store token separately in localStorage, not in zustand persist
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

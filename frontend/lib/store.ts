"use client";

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { API_ENDPOINTS } from './api';

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
  archivedText?: string;
  extractionType?: 'fast' | 'complete';
  processingStatus: 'pending' | 'processed' | 'failed';
  createdAt: string;
  updatedAt: string;
  archivedAt?: string; // For soft delete
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
  items: SavedItem[];
  tags: TagWithCount[];
  chatThreads: ChatThread[];
  _hasHydrated: boolean;
  setHasHydrated: (state: boolean) => void;
  
  // Actions
  register: (email: string, password: string, name: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (name: string, email: string) => void;
  updatePreferences: (preferences: Partial<User['preferences']>) => void;
  
  fetchItems: (searchQuery?: string, tags?: string[]) => Promise<void>;
  fetchTags: () => Promise<void>;
  addItem: (item: Omit<SavedItem, 'id' | 'createdAt' | 'updatedAt' | 'ownerId'>) => Promise<string>;
  updateItem: (id: string, updates: Partial<SavedItem>) => Promise<void>;
  deleteItem: (id: string) => Promise<void>; // Soft delete
  restoreItem: (id: string) => void;
  permanentlyDeleteItem: (id: string) => void;
  
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
      items: [],
      tags: [],
      chatThreads: [],
      _hasHydrated: false,
      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },

      register: async (email, password, name) => {
        try {
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
          
          // Fetch items after successful registration
          await get().fetchItems();
        } catch (error) {
          console.error('Registration error:', error);
          throw error;
        }
      },

      login: async (email, password) => {
        try {
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
          
          // Fetch items after successful login
          await get().fetchItems();
        } catch (error) {
          console.error('Login error:', error);
          throw error;
        }
      },

      logout: () => {
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
          }).catch(err => console.error('Logout error:', err));
        }
        
        set({ currentUser: null, token: null });
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

      fetchItems: async (searchQuery?: string, tags?: string[]) => {
        const { token } = get();
        if (!token) return;

        try {
          // Build query parameters
          const params = new URLSearchParams();
          if (searchQuery && searchQuery.trim()) {
            params.append('search', searchQuery.trim());
          }
          if (tags && tags.length > 0) {
            params.append('tags', tags.join(','));
          }

          const url = `${API_ENDPOINTS.items}${params.toString() ? `?${params.toString()}` : ''}`;
          
          const response = await fetch(url, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            if (response.status === 401) {
              // Clear token and redirect to login
              localStorage.removeItem('token');
              set({ currentUser: null, token: null });
              window.location.href = '/login';
              return;
            }
            throw new Error('Failed to fetch items');
          }

          const itemsData = await response.json();
          
          // Convert snake_case to camelCase for all items
          const formattedItems: SavedItem[] = itemsData.map((item: Record<string, unknown>) => ({
            id: item.id,
            ownerId: item.owner_id,
            url: item.url,
            title: item.title,
            description: item.description,
            imageUrl: item.image_url,
            faviconUrl: item.favicon_url,
            notesMarkdown: item.notes_markdown,
            tags: item.tags || [],
            suggestedTags: item.suggested_tags,
            suggestedTopic: item.suggested_topic,
            archivedText: item.archived_text,
            extractionType: item.extraction_type as 'fast' | 'complete' | undefined,
            processingStatus: item.processing_status,
            createdAt: item.created_at,
            updatedAt: item.updated_at,
            archivedAt: item.archived_at,
          }));

          set({ items: formattedItems });
        } catch (error) {
          console.error('Failed to fetch items:', error);
        }
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
              extraction_type: itemData.extractionType,  // Convert camelCase to snake_case
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
            extractionType: newItem.extraction_type as 'fast' | 'complete' | undefined,
            processingStatus: newItem.processing_status,
            createdAt: newItem.created_at,
            updatedAt: newItem.updated_at,
            archivedAt: newItem.archived_at,
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
              extraction_type: updates.extractionType,
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
            archivedText: updatedItem.archived_text,
            extractionType: updatedItem.extraction_type as 'fast' | 'complete' | undefined,
            processingStatus: updatedItem.processing_status,
            createdAt: updatedItem.created_at,
            updatedAt: updatedItem.updated_at,
            archivedAt: updatedItem.archived_at,
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

          // Remove from local state (soft delete - filter out)
          const { items } = get();
          set({
            items: items.filter(item => item.id !== id)
          });
        } catch (error) {
          console.error('Failed to delete item:', error);
          throw error;
        }
      },

      restoreItem: (id) => {
        const { items } = get();
        set({
          items: items.map(item => 
            item.id === id 
              ? { ...item, archivedAt: undefined } 
              : item
          )
        });
      },

      permanentlyDeleteItem: (id) => {
        const { items } = get();
        set({ items: items.filter(item => item.id !== id) });
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
      name: 'stash-storage',
      partialize: (state) => ({
        items: state.items,
        chatThreads: state.chatThreads,
        // Store token separately in localStorage, not in zustand persist
        // currentUser will be fetched from /me endpoint on app load
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

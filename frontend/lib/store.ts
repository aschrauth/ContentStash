"use client";

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

// --- Types ---

export type User = {
  id: string;
  email: string;
  name: string;
  passwordHash: string; // Simulated hash
  createdAt: string;
  preferences?: {
    viewMode: 'grid' | 'list';
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
  processingStatus: 'pending' | 'processed' | 'failed';
  createdAt: string;
  updatedAt: string;
  archivedAt?: string; // For soft delete
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: {
    savedItemId: string;
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
  messages: ChatMessage[];
};

// --- Store ---

interface AppState {
  currentUser: User | null;
  users: User[];
  items: SavedItem[];
  chatThreads: ChatThread[];
  
  // Actions
  register: (email: string, password: string, name: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (name: string, email: string) => void;
  updatePreferences: (preferences: Partial<User['preferences']>) => void;
  
  addItem: (item: Omit<SavedItem, 'id' | 'createdAt' | 'updatedAt' | 'ownerId'>) => Promise<string>;
  updateItem: (id: string, updates: Partial<SavedItem>) => void;
  deleteItem: (id: string) => void; // Soft delete
  restoreItem: (id: string) => void;
  permanentlyDeleteItem: (id: string) => void;
  
  addChatThread: (firstMessage: string) => string;
  addChatMessage: (threadId: string, message: Omit<ChatMessage, 'id' | 'createdAt'>) => void;
  deleteChatThread: (id: string) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      currentUser: null,
      users: [],
      items: [],
      chatThreads: [],

      register: async (email, password, name) => {
        const { users } = get();
        if (users.find(u => u.email === email)) {
          throw new Error("User already exists");
        }
        const newUser: User = {
          id: uuidv4(),
          email,
          name,
          passwordHash: btoa(password), // Simple mock hash
          createdAt: new Date().toISOString(),
          preferences: { viewMode: 'list' }, // Default preference set to list
        };
        set({ users: [...users, newUser], currentUser: newUser });
      },

      login: async (email, password) => {
        const { users } = get();
        const user = users.find(u => u.email === email && u.passwordHash === btoa(password));
        if (!user) {
          throw new Error("Invalid credentials");
        }
        set({ currentUser: user });
      },

      logout: () => {
        set({ currentUser: null });
      },

      updateProfile: (name, email) => {
        const { currentUser, users } = get();
        if (!currentUser) return;
        
        const updatedUser = { ...currentUser, name, email };
        set({
          currentUser: updatedUser,
          users: users.map(u => u.id === currentUser.id ? updatedUser : u)
        });
      },

      updatePreferences: (preferences) => {
        const { currentUser, users } = get();
        if (!currentUser) return;

        const updatedUser = { 
          ...currentUser, 
          preferences: { ...currentUser.preferences, ...preferences } 
        };

        set({
          currentUser: updatedUser,
          users: users.map(u => u.id === currentUser.id ? updatedUser : u)
        });
      },

      addItem: async (itemData) => {
        const { currentUser, items } = get();
        if (!currentUser) throw new Error("Not authenticated");

        const newItem: SavedItem = {
          id: uuidv4(),
          ownerId: currentUser.id,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          ...itemData,
        };

        set({ items: [newItem, ...items] });
        return newItem.id;
      },

      updateItem: (id, updates) => {
        const { items } = get();
        set({
          items: items.map(item => 
            item.id === id 
              ? { ...item, ...updates, updatedAt: new Date().toISOString() } 
              : item
          )
        });
      },

      deleteItem: (id) => {
        const { items } = get();
        set({
          items: items.map(item => 
            item.id === id 
              ? { ...item, archivedAt: new Date().toISOString() } 
              : item
          )
        });
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

      addChatThread: (firstMessage) => {
        const { currentUser, chatThreads } = get();
        if (!currentUser) throw new Error("Not authenticated");

        const newThread: ChatThread = {
          id: uuidv4(),
          ownerId: currentUser.id,
          title: firstMessage.slice(0, 30) + (firstMessage.length > 30 ? '...' : ''),
          messages: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        set({ chatThreads: [newThread, ...chatThreads] });
        return newThread.id;
      },

      addChatMessage: (threadId, message) => {
        const { chatThreads } = get();
        const newMessage: ChatMessage = {
          id: uuidv4(),
          createdAt: new Date().toISOString(),
          ...message,
        };

        set({
          chatThreads: chatThreads.map(thread => 
            thread.id === threadId 
              ? { ...thread, messages: [...thread.messages, newMessage], updatedAt: new Date().toISOString() } 
              : thread
          )
        });
      },

      deleteChatThread: (id) => {
        const { chatThreads } = get();
        set({ chatThreads: chatThreads.filter(t => t.id !== id) });
      },
    }),
    {
      name: 'stash-storage',
      partialize: (state) => ({
        users: state.users,
        items: state.items,
        chatThreads: state.chatThreads,
        // Don't persist currentUser session automatically if we wanted strict security, 
        // but for MVP convenience we will to keep them logged in on refresh.
        currentUser: state.currentUser, 
      }),
    }
  )
);


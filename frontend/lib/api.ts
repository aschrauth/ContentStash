/**
 * API Configuration
 * Central configuration for API endpoints
 */

import type { SavedItem } from './store';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;
  bodyText?: string;

  constructor(message: string, status: number, bodyText?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.bodyText = bodyText;
  }
}

export const isApiError = (error: unknown): error is ApiError => {
  return error instanceof ApiError;
};

/**
 * API endpoints
 */
export const API_ENDPOINTS = {
  // Auth
  signup: `${API_BASE_URL}/auth/signup`,
  login: `${API_BASE_URL}/auth/login`,
  logout: `${API_BASE_URL}/auth/logout`,
  me: `${API_BASE_URL}/auth/me`,
  
  // Items
  items: `${API_BASE_URL}/items`,
  itemById: (id: string) => `${API_BASE_URL}/items/${id}`,
  itemReprocess: (id: string) => `${API_BASE_URL}/items/${id}/reprocess`,
  itemPreview: `${API_BASE_URL}/items/preview`,
  itemGenerateMetadata: `${API_BASE_URL}/items/generate-metadata`,
  
  // Tags
  tags: `${API_BASE_URL}/tags`,
  tagsAutocomplete: (query: string) => `${API_BASE_URL}/tags/autocomplete?q=${encodeURIComponent(query)}`,
  
  // Chat
  chatThreads: `${API_BASE_URL}/chat/threads`,
  chatThreadById: (id: string) => `${API_BASE_URL}/chat/threads/${id}`,
  chatThreadMessages: (id: string) => `${API_BASE_URL}/chat/threads/${id}/messages`,
  
  // Collections
  collections: `${API_BASE_URL}/collections`,
  collectionById: (id: string) => `${API_BASE_URL}/collections/${id}`,
  
  // Search
  search: `${API_BASE_URL}/search`,
  
  // Health
  health: 'http://localhost:8000/healthz',
} as const;

/**
 * API helper functions
 */

export interface PaginationMetadata {
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
  total: number;
  unread?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMetadata;
}

export interface RawSavedItem {
  id: string;
  owner_id: string;
  url?: string;
  title: string;
  description?: string;
  image_url?: string;
  favicon_url?: string;
  notes_markdown?: string;
  tags?: string[];
  suggested_tags?: string[];
  suggested_topic?: string;
  ai_summary?: string;
  archived_text?: string;
  source?: string;
  word_count?: number;
  extraction_type?: SavedItem['extractionType'];
  processing_status: SavedItem['processingStatus'];
  processing_error?: string;
  is_read?: boolean;
  created_at: string;
  updated_at: string;
}

export type GetItemsResponse = PaginatedResponse<RawSavedItem> | RawSavedItem[];

export const normalizeSavedItem = (item: RawSavedItem): SavedItem => ({
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
  aiSummary: item.ai_summary,
  archivedText: item.archived_text,
  source: item.source,
  wordCount: item.word_count,
  extractionType: item.extraction_type,
  processingStatus: item.processing_status,
  isRead: item.is_read === true,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
});

/**
 * Get items with pagination support
 */
export const getItems = async (
  token: string,
  search?: string,
  tags?: string[],
  limit: number = 50,
  cursor?: string
): Promise<GetItemsResponse> => {
  const params = new URLSearchParams();
  
  if (search && search.trim()) {
    params.append('search', search.trim());
  }
  
  if (tags && tags.length > 0) {
    params.append('tags', tags.join(','));
  }
  
  params.append('limit', limit.toString());
  
  if (cursor) {
    params.append('cursor', cursor);
  }
  
  const url = `${API_ENDPOINTS.items}${params.toString() ? `?${params.toString()}` : ''}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    let bodyText: string | undefined;
    try {
      bodyText = await response.text();
    } catch {
      // ignore
    }
    throw new ApiError('Failed to fetch items', response.status, bodyText);
  }
  
  return response.json() as Promise<GetItemsResponse>;
};

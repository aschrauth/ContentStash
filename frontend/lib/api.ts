/**
 * API Configuration
 * Central configuration for API endpoints
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMetadata;
}

/**
 * Get items with pagination support
 */
export const getItems = async (
  token: string,
  search?: string,
  tags?: string[],
  limit: number = 50,
  cursor?: string
): Promise<PaginatedResponse<any>> => {
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
    throw new Error('Failed to fetch items');
  }
  
  return response.json();
};
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
  login: `${API_BASE_URL}/auth/login`,
  register: `${API_BASE_URL}/auth/register`,
  logout: `${API_BASE_URL}/auth/logout`,
  
  // Items
  items: `${API_BASE_URL}/items`,
  itemById: (id: string) => `${API_BASE_URL}/items/${id}`,
  
  // Collections
  collections: `${API_BASE_URL}/collections`,
  collectionById: (id: string) => `${API_BASE_URL}/collections/${id}`,
  
  // Search
  search: `${API_BASE_URL}/search`,
  
  // Health
  health: 'http://localhost:8000/healthz',
} as const;
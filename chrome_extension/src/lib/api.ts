import type { SavedItem, CreateItemRequest, UploadContentRequest, PendingLocalHint } from '../types';

export class ApiError extends Error {
  public status: number;
  public body: string;

  constructor(status: number, body: string, prefix: string = 'API Error') {
    super(`${prefix}: ${status} - ${body}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export class ContentStashAPI {
  public baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new ApiError(response.status, error);
    }

    return response.json();
  }

  async login(email: string, password: string): Promise<{ token: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new ApiError(response.status, error, 'Login failed');
    }

    return response.json();
  }

  async getCurrentUser(): Promise<unknown> {
    return this.request<unknown>('/api/v1/auth/me');
  }

  async createItem(data: CreateItemRequest): Promise<SavedItem> {
    return this.request<SavedItem>('/api/v1/items', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPendingLocalItems(): Promise<SavedItem[]> {
    return this.request<SavedItem[]>('/api/v1/items/pending-local');
  }

  async getPendingLocalHint(): Promise<PendingLocalHint> {
    return this.request<PendingLocalHint>('/api/v1/items/pending-local/hint');
  }

  async uploadContent(itemId: string, data: UploadContentRequest): Promise<SavedItem> {
    return this.request<SavedItem>(`/api/v1/items/${itemId}/content`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async updateItemMetadata(itemId: string, metadata: {
    title?: string;
    description?: string;
    image_url?: string;
  }): Promise<SavedItem> {
    return this.request<SavedItem>(`/api/v1/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(metadata),
    });
  }
}

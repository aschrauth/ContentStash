const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export function getServerApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_URL;
}

export function getServerApiUrl(path: string): string {
  const baseUrl = getServerApiBaseUrl().replace(/\/$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  return `${baseUrl}${normalizedPath}`;
}

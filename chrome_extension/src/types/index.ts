export type ExtractionType = 'fast' | 'complete' | 'local';

export interface SavedItem {
  id: string;
  owner_id: string;
  url?: string;
  title: string;
  description?: string;
  image_url?: string;
  favicon_url?: string;
  notes_markdown?: string;
  tags: string[];
  archived_text?: string;
  extraction_type: ExtractionType;
  suggested_tags?: string[];
  suggested_topic?: string;
  processing_status: 'pending' | 'processed' | 'failed' | 'pending_local_extraction';
  processing_error?: string;
  source?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  token?: string;
  serverUrl: string;
}

export interface ExtensionSettings {
  serverUrl: string;
  popupCloseDelayMs: number;
}

export interface CreateItemRequest {
  url?: string;
  title: string;
  description?: string;
  image_url?: string;
  favicon_url?: string;
  tags?: string[];
  extraction_type?: ExtractionType;
}

export interface UploadContentRequest {
  content: string;
  extraction_source: string;
  source?: string;
}

export interface PendingLocalHint {
  pending_count: number;
  queue_version: string;
  recommended_poll_seconds: number;
}

export interface YouTubeMetadata {
  title: string;
  author: string;
  videoId: string;
  lengthSeconds: number;
  captionUrl: string | null;
  channelName?: string;
}

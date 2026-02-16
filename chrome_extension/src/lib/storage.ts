import type { AuthState, ExtensionSettings } from '../types';

const DEFAULT_SETTINGS: ExtensionSettings = {
  serverUrl: 'http://localhost:8000',
  popupCloseDelayMs: 1000,
};

export class Storage {
  static async getAuthState(): Promise<AuthState> {
    const result = await chrome.storage.local.get(['token', 'serverUrl']);
    return {
      isAuthenticated: !!result.token,
      token: result.token,
      serverUrl: result.serverUrl || DEFAULT_SETTINGS.serverUrl,
    };
  }

  static async setAuthState(token: string, serverUrl: string): Promise<void> {
    await chrome.storage.local.set({ token, serverUrl });
  }

  static async clearAuth(): Promise<void> {
    await chrome.storage.local.remove(['token']);
  }

  static async getSettings(): Promise<ExtensionSettings> {
    const result = await chrome.storage.local.get([
      'serverUrl',
      'popupCloseDelayMs',
    ]);
    
    return {
      serverUrl: result.serverUrl || DEFAULT_SETTINGS.serverUrl,
      popupCloseDelayMs: result.popupCloseDelayMs ?? DEFAULT_SETTINGS.popupCloseDelayMs,
    };
  }

  static async updateSettings(settings: Partial<ExtensionSettings>): Promise<void> {
    await chrome.storage.local.set(settings);
  }
}
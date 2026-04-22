import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { ApiError, ContentStashAPI } from '../lib/api';
import { Storage } from '../lib/storage';
import type { ExtractionType } from '../types';
import './popup.css';

const api = new ContentStashAPI();

function isIntermediaryUrl(value?: string): boolean {
  if (!value) return false;
  try {
    const host = new URL(value).hostname.toLowerCase().replace(/^www\./, '');
    return host === 'apple.news' ||
      host.endsWith('.apple.news') ||
      host === 'flip.it' ||
      host.endsWith('.flip.it') ||
      host === 'flipboard.com' ||
      host.endsWith('.flipboard.com');
  } catch {
    return false;
  }
}

function looksLikeIntermediaryTitle(value?: string): boolean {
  const normalized = (value || '').trim().toLowerCase();
  return !normalized ||
    normalized.includes('opening story') ||
    normalized.includes('apple news') ||
    normalized.includes('flipboard');
}

async function resolveActiveIntermediaryTarget(tabId: number, originalUrl: string): Promise<string | null> {
  if (!isIntermediaryUrl(originalUrl)) {
    return null;
  }

  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const ignoredDomains = [
        'apple.com',
        'itunes.apple.com',
        'apps.apple.com',
        'flipboard.com',
        'flip.it',
        'facebook.com',
        'twitter.com',
        'x.com',
        'linkedin.com',
        'pinterest.com',
      ];

      const hostOf = (value: string) => {
        try {
          return new URL(value).hostname.toLowerCase().replace(/^www\./, '');
        } catch {
          return '';
        }
      };

      const isIgnored = (value: string) => {
        const host = hostOf(value);
        return ignoredDomains.some(domain => host === domain || host.endsWith(`.${domain}`));
      };

      const cleanUrl = (value: string | null | undefined) => {
        if (!value) return null;
        try {
          return new URL(decodeURIComponent(value.replace(/\\\//g, '/').trim()), window.location.href).href;
        } catch {
          return null;
        }
      };

      const isCandidate = (value: string | null) => {
        if (!value || !/^https?:\/\//i.test(value)) return false;
        if (isIgnored(value)) return false;
        if (/\.(css|js|png|jpe?g|gif|svg|ico)$/i.test(new URL(value).pathname)) return false;
        return true;
      };

      const refresh = document.querySelector('meta[http-equiv="refresh" i]')?.getAttribute('content') || '';
      const refreshMatch = refresh.match(/url\s*=\s*([^;]+)/i);
      if (refreshMatch) {
        const candidate = cleanUrl(refreshMatch[1]);
        if (isCandidate(candidate)) return candidate;
      }

      const selectors = [
        'meta[property="og:url"]',
        'meta[name="twitter:url"]',
        'link[rel="canonical"]',
        'link[rel="amphtml"]',
      ];
      for (const selector of selectors) {
        const element = document.querySelector(selector);
        const candidate = cleanUrl(element?.getAttribute('content') || element?.getAttribute('href'));
        if (isCandidate(candidate)) return candidate;
      }

      const linkText = /\b(click|tap|open|read|continue|view|source|original|story|article)\b/i;
      const anchors = Array.from(document.querySelectorAll<HTMLAnchorElement>('a[href]'))
        .map(anchor => {
          const candidate = cleanUrl(anchor.getAttribute('href'));
          if (!isCandidate(candidate)) return null;
          const text = (anchor.innerText || anchor.textContent || '').trim();
          let score = linkText.test(text) ? 100 : 0;
          score += Math.min(new URL(candidate!).pathname.split('/').filter(Boolean).length * 10, 30);
          return { candidate, score };
        })
        .filter((entry): entry is { candidate: string; score: number } => Boolean(entry))
        .sort((a, b) => b.score - a.score);

      return anchors[0]?.candidate || null;
    },
  });

  return (results[0]?.result as string | null | undefined) || null;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');
  const [extractionType, setExtractionType] = useState<ExtractionType>('fast');
  const [pendingCount, setPendingCount] = useState(0);
  const [message, setMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [popupCloseDelay, setPopupCloseDelay] = useState(1000);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    checkAuth();
    loadPendingCount();
    loadSettings();
  }, []);

  function isUnauthorizedError(error: unknown): boolean {
    if (error instanceof ApiError) {
      return error.status === 401 || error.status === 403;
    }

    return /401|403|Invalid authentication credentials/i.test((error as Error)?.message || '');
  }

  async function resetToLogin(messageText = 'Session expired. Please log in again.') {
    await Storage.clearAuth();
    api.setToken(null);
    setIsAuthenticated(false);
    setPendingCount(0);
    setShowSettings(false);
    setMessage(messageText);
  }

  async function checkAuth() {
    const authState = await Storage.getAuthState();
    setServerUrl(authState.serverUrl);
    api.baseUrl = authState.serverUrl;

    if (!authState.isAuthenticated || !authState.token) {
      setIsAuthenticated(false);
      setIsLoading(false);
      return;
    }

    api.setToken(authState.token);
    try {
      await api.getCurrentUser();
      setIsAuthenticated(true);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        await resetToLogin();
      } else {
        setIsAuthenticated(true);
      }
    }

    setIsLoading(false);
  }

  async function loadPendingCount() {
    try {
      const authState = await Storage.getAuthState();
      if (authState.isAuthenticated && authState.token) {
        api.baseUrl = authState.serverUrl;
        api.setToken(authState.token);
        const items = await api.getPendingLocalItems();
        setPendingCount(items.length);
      }
    } catch (error) {
      if (isUnauthorizedError(error)) {
        await resetToLogin();
      }
      console.error('Failed to load pending count:', error);
    }
  }

  async function loadSettings() {
    try {
      const settings = await Storage.getSettings();
      setPopupCloseDelay(settings.popupCloseDelayMs);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }

  async function handleSaveSettings() {
    setMessage('');
    setIsProcessing(true);

    try {
      await Storage.updateSettings({
        popupCloseDelayMs: popupCloseDelay,
      });

      setMessage('✓ Settings saved');
      setTimeout(() => {
        window.close();
      }, popupCloseDelay);
    } catch (error) {
      setMessage('✗ Failed to save settings: ' + (error as Error).message);
      setIsProcessing(false);
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setMessage('');

    try {
      api.baseUrl = serverUrl;
      const result = await api.login(email, password);
      await Storage.setAuthState(result.token, serverUrl);
      api.setToken(result.token);
      setIsAuthenticated(true);
      setMessage('✓ Logged in successfully');
      loadPendingCount();
      await chrome.runtime.sendMessage({ type: 'PROCESS_PENDING_NOW' });
    } catch (error) {
      setMessage('✗ Login failed: ' + (error as Error).message);
    }
  }

  async function handleLogout() {
    await Storage.clearAuth();
    api.setToken(null);
    setIsAuthenticated(false);
    setEmail('');
    setPassword('');
    setMessage('Logged out');
  }

  async function handleSaveCurrentTab() {
    setMessage('');
    setIsProcessing(true);

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.url || !tab.title || !tab.id) {
        setMessage('✗ Cannot save this page');
        setIsProcessing(false);
        return;
      }

      // For local extraction, extract content immediately
      if (extractionType === 'local') {
        setMessage('Extracting content...');

        const isIntermediaryPage = isIntermediaryUrl(tab.url);
        const resolvedIntermediaryUrl = await resolveActiveIntermediaryTarget(tab.id, tab.url);
        if (isIntermediaryPage) {
          const urlForQueuedExtraction = resolvedIntermediaryUrl || tab.url;
          const item = await api.createItem({
            url: urlForQueuedExtraction,
            title: looksLikeIntermediaryTitle(tab.title) ? urlForQueuedExtraction : tab.title,
            extraction_type: 'local',
          });

          if (item.id) {
            await chrome.runtime.sendMessage({ type: 'PROCESS_PENDING_NOW' });
          }

          setMessage('✓ Saved with local extraction!');
          setTimeout(() => {
            window.close();
          }, popupCloseDelay);
          return;
        }

        // Extract metadata using executeScript
        const metadataResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const url = window.location.href;
            const isYouTube = url.includes('youtube.com/watch');

            const getMetaContent = (name: string): string | null => {
              const meta = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
              return meta?.getAttribute('content') || null;
            };

            // Enhanced YouTube Extraction
            if (isYouTube) {
              let videoId = null;
              const videoIdMatch = url.match(/[?&]v=([^&]+)/);
              if (videoIdMatch) {
                videoId = videoIdMatch[1];
              }

              // 1. Image: Construction from ID is most reliable for navigation
              let image = '';
              if (videoId) {
                image = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
              } else {
                image = getMetaContent('og:image') || '';
              }

              // 2. Description: Try DOM first (updates on nav), then meta
              let description = '';

              // Try to find the description text in the DOM
              // These selectors target the expandable description box
              const descSelectors = [
                '#description-inline-expander .ytd-text-inline-expander',
                '#description-text',
                '#description .content'
              ];

              for (const selector of descSelectors) {
                const el = document.querySelector(selector);
                if (el && el.textContent) {
                  description = el.textContent.trim();
                  // Break if we found a good description
                  if (description.length > 20) break;
                }
              }

              // Fallback to meta if DOM failed
              if (!description) {
                description = getMetaContent('og:description') ||
                  getMetaContent('description') || '';
              }

              return {
                description,
                image_url: image
              };
            }

            // Standard Extraction for other sites
            const description = getMetaContent('og:description') ||
              getMetaContent('description') ||
              getMetaContent('twitter:description') || '';

            const image = getMetaContent('og:image') ||
              getMetaContent('twitter:image') || '';

            return {
              description,
              image_url: image,
            };
          }
        });

        const metadata = metadataResults[0]?.result;

        // Request content extraction from the content script
        let contentResponse;
        try {
          contentResponse = await chrome.tabs.sendMessage(tab.id, { type: 'EXTRACT_CONTENT' });
        } catch (error) {
          setMessage('✗ Failed to communicate with content script. Please refresh the page and try again.');
          setIsProcessing(false);
          return;
        }

        if (!contentResponse?.success || !contentResponse?.content) {
          setMessage('✗ Failed to extract content: ' + (contentResponse?.error || 'Unknown error'));
          setIsProcessing(false);
          return;
        }

        // Create item with extracted data
        const item = await api.createItem({
          url: tab.url,
          title: tab.title,
          description: contentResponse?.metadata?.description || metadata?.description || undefined,
          image_url: metadata?.image_url || undefined,
          extraction_type: 'local',
        });

        // Upload the extracted content from content script
        if (item.id) {
          await api.uploadContent(item.id, {
            content: contentResponse.content,
            extraction_source: 'chrome_extension_content_script',
          });
        }

        setMessage('✓ Saved with local extraction!');
        await chrome.runtime.sendMessage({ type: 'PROCESS_PENDING_NOW' });
      } else {
        // For fast/complete, extract metadata and send to server
        setMessage('Extracting metadata...');

        // Extract metadata using executeScript
        const metadataResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const url = window.location.href;
            const isYouTube = url.includes('youtube.com/watch');

            const getMetaContent = (name: string): string | null => {
              const meta = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
              return meta?.getAttribute('content') || null;
            };

            // Enhanced YouTube Extraction
            if (isYouTube) {
              let videoId = null;
              const videoIdMatch = url.match(/[?&]v=([^&]+)/);
              if (videoIdMatch) {
                videoId = videoIdMatch[1];
              }

              // 1. Image: Construction from ID is most reliable for navigation
              let image = '';
              if (videoId) {
                image = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
              } else {
                image = getMetaContent('og:image') || '';
              }

              // 2. Description: Try DOM first (updates on nav), then meta
              let description = '';

              // Try to find the description text in the DOM
              // These selectors target the expandable description box
              const descSelectors = [
                '#description-inline-expander .ytd-text-inline-expander',
                '#description-text',
                '#description .content'
              ];

              for (const selector of descSelectors) {
                const el = document.querySelector(selector);
                if (el && el.textContent) {
                  description = el.textContent.trim();
                  // Break if we found a good description
                  if (description.length > 20) break;
                }
              }

              // Fallback to meta if DOM failed
              if (!description) {
                description = getMetaContent('og:description') ||
                  getMetaContent('description') || '';
              }

              return {
                description,
                image_url: image
              };
            }

            // Standard Extraction for other sites
            const description = getMetaContent('og:description') ||
              getMetaContent('description') ||
              getMetaContent('twitter:description') || '';

            const image = getMetaContent('og:image') ||
              getMetaContent('twitter:image') || '';

            return {
              description,
              image_url: image,
            };
          }
        });

        const metadata = metadataResults[0]?.result;

        // Create item with metadata and let server handle extraction
        await api.createItem({
          url: tab.url,
          title: tab.title,
          description: metadata?.description || undefined,
          image_url: metadata?.image_url || undefined,
          extraction_type: extractionType,
        });

        setMessage('✓ Saved successfully!');
        await chrome.runtime.sendMessage({ type: 'PROCESS_PENDING_NOW' });
      }

      setTimeout(() => {
        window.close();
      }, popupCloseDelay);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        await resetToLogin();
        setIsProcessing(false);
        return;
      }
      setMessage('✗ Failed to save: ' + (error as Error).message);
      setIsProcessing(false);
    }
  }

  async function handleProcessPending() {
    setMessage('Processing pending items...');
    setIsProcessing(true);

    try {
      await chrome.runtime.sendMessage({ type: 'PROCESS_PENDING_NOW' });
      setMessage('✓ Processing started');
      setTimeout(() => {
        window.close();
      }, popupCloseDelay);
    } catch (error) {
      setMessage('✗ Failed: ' + (error as Error).message);
      setIsProcessing(false);
    }
  }

  if (isLoading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="container">
        <h1>ContentStash</h1>
        <form onSubmit={handleLogin} className="login-form">
          <input
            type="url"
            placeholder="Server URL"
            value={serverUrl}
            onChange={(e) => setServerUrl(e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">Login</button>
        </form>
        {message && <p className="message">{message}</p>}
      </div>
    );
  }

  return (
    <div className="container">
      {isProcessing ? (
        <div className="processing-view">
          {message && <p className="message">{message}</p>}
        </div>
      ) : (
        <>
          <div className="header">
            <h1>ContentStash</h1>
            <div className="header-buttons">
              <button onClick={() => setShowSettings(!showSettings)} className="settings-btn">
                {showSettings ? 'Hide Settings' : 'Settings'}
              </button>
              <button onClick={handleLogout} className="logout-btn">Logout</button>
            </div>
          </div>

          {showSettings ? (
            <div className="settings-section">
              <h2>Settings</h2>

              <div className="setting-group">
                <label className="setting-label">
                  Popup auto-close delay (milliseconds):
                  <input
                    type="number"
                    min="0"
                    max="5000"
                    step="100"
                    value={popupCloseDelay}
                    onChange={(e) => setPopupCloseDelay(parseInt(e.target.value) || 1000)}
                    className="interval-input"
                  />
                </label>
                <p className="setting-hint">
                  How long to wait before closing the popup after a successful save (0-5000ms)
                </p>
              </div>

              <button onClick={handleSaveSettings} className="save-settings-btn">
                Save Settings
              </button>
            </div>
          ) : (
            <>
              <div className="save-section">
                <h2>Save Current Page</h2>
                <div className="extraction-type">
                  <label>
                    <input
                      type="radio"
                      value="fast"
                      checked={extractionType === 'fast'}
                      onChange={(e) => setExtractionType(e.target.value as ExtractionType)}
                    />
                    Fast (Server)
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="complete"
                      checked={extractionType === 'complete'}
                      onChange={(e) => setExtractionType(e.target.value as ExtractionType)}
                    />
                    Complete (Server)
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="local"
                      checked={extractionType === 'local'}
                      onChange={(e) => setExtractionType(e.target.value as ExtractionType)}
                    />
                    Local (Browser)
                  </label>
                </div>
                <button onClick={handleSaveCurrentTab} className="save-btn">
                  Save Page
                </button>
              </div>

              <div className="pending-section">
                <h2>Local Extraction Queue</h2>
                <p>{pendingCount} item(s) pending</p>
                <button onClick={handleProcessPending} className="process-btn">
                  Process Now
                </button>
              </div>
            </>
          )}

          {message && <p className="message">{message}</p>}
        </>
      )}
    </div>
  );
}

const root = createRoot(document.getElementById('root')!);
root.render(<App />);

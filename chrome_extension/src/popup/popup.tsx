import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { ContentStashAPI } from '../lib/api';
import { Storage } from '../lib/storage';
import type { ExtractionType } from '../types';
import './popup.css';

const api = new ContentStashAPI();

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
  const [pollingEnabled, setPollingEnabled] = useState(true);
  const [pollingInterval, setPollingInterval] = useState(15);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    checkAuth();
    loadPendingCount();
    loadSettings();
  }, []);

  async function checkAuth() {
    const authState = await Storage.getAuthState();
    setIsAuthenticated(authState.isAuthenticated);
    setServerUrl(authState.serverUrl);
    if (authState.token) {
      api.setToken(authState.token);
    }
    setIsLoading(false);
  }

  async function loadPendingCount() {
    try {
      const authState = await Storage.getAuthState();
      if (authState.isAuthenticated && authState.token) {
        api.setToken(authState.token);
        const items = await api.getPendingLocalItems();
        setPendingCount(items.length);
      }
    } catch (error) {
      console.error('Failed to load pending count:', error);
    }
  }

  async function loadSettings() {
    try {
      const settings = await Storage.getSettings();
      setPollingEnabled(settings.pollingEnabled);
      setPollingInterval(settings.pollingIntervalMinutes);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }

  async function handleSaveSettings() {
    setMessage('');
    setIsProcessing(true);
    
    try {
      await Storage.updateSettings({
        pollingEnabled,
        pollingIntervalMinutes: pollingInterval,
      });
      
      // Notify service worker to update polling alarm
      await chrome.runtime.sendMessage({
        type: 'UPDATE_POLLING_SETTINGS',
        payload: {
          enabled: pollingEnabled,
          intervalMinutes: pollingInterval,
        },
      });
      
      setMessage('✓ Settings saved');
      setTimeout(() => {
        window.close();
      }, 500);
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
    } catch (error) {
      setMessage('✗ Login failed: ' + (error as Error).message);
    }
  }

  async function handleLogout() {
    await Storage.clearAuth();
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
        
        // Extract metadata using executeScript
        const metadataResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const getMetaContent = (name: string): string | null => {
              const meta = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
              return meta?.getAttribute('content') || null;
            };

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
          description: metadata?.description || undefined,
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
      } else {
        // For fast/complete, just send URL and let server handle it
        await api.createItem({
          url: tab.url,
          title: tab.title,
          extraction_type: extractionType,
        });

        setMessage('✓ Saved successfully!');
      }
      
      setTimeout(() => {
        window.close();
      }, 500);
    } catch (error) {
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
      }, 500);
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
                  <input
                    type="checkbox"
                    checked={pollingEnabled}
                    onChange={(e) => setPollingEnabled(e.target.checked)}
                  />
                  Enable automatic polling for pending items
                </label>
              </div>

              <div className="setting-group">
                <label className="setting-label">
                  Polling interval (minutes):
                  <input
                    type="number"
                    min="1"
                    max="1440"
                    value={pollingInterval}
                    onChange={(e) => setPollingInterval(parseInt(e.target.value) || 15)}
                    disabled={!pollingEnabled}
                    className="interval-input"
                  />
                </label>
                <p className="setting-hint">
                  How often to check for items that need local extraction (1-1440 minutes)
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
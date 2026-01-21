import { ContentStashAPI } from '../lib/api';
import { Storage } from '../lib/storage';
import type { SavedItem } from '../types';

const api = new ContentStashAPI();

// Initialize on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log('ContentStash extension installed');
  
  // Set up polling alarm
  const settings = await Storage.getSettings();
  if (settings.pollingEnabled) {
    await setupPollingAlarm(settings.pollingIntervalMinutes);
  }
});

// Set up polling alarm
async function setupPollingAlarm(intervalMinutes: number) {
  await chrome.alarms.clear('pollPendingItems');
  await chrome.alarms.create('pollPendingItems', {
    periodInMinutes: intervalMinutes,
  });
  console.log(`Polling alarm set for every ${intervalMinutes} minutes`);
}

// Handle alarm for polling
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'pollPendingItems') {
    await processPendingItems();
  }
});

// Process pending local extraction items
async function processPendingItems() {
  try {
    const authState = await Storage.getAuthState();
    
    if (!authState.isAuthenticated || !authState.token) {
      console.log('Not authenticated, skipping polling');
      return;
    }

    api.setToken(authState.token);
    const pendingItems = await api.getPendingLocalItems();
    
    console.log(`Found ${pendingItems.length} items pending local extraction`);
    
    for (const item of pendingItems) {
      await processItem(item);
    }
  } catch (error) {
    console.error('Error processing pending items:', error);
  }
}

// Process a single item
async function processItem(item: SavedItem) {
  if (!item.url) {
    console.warn(`Item ${item.id} has no URL, skipping`);
    return;
  }

  try {
    console.log(`Processing item ${item.id}: ${item.url}`);
    
    // Create a new tab in the background
    const tab = await chrome.tabs.create({
      url: item.url,
      active: false,
      pinned: true,
    });

    // Wait for the tab to load
    await new Promise<void>((resolve) => {
      const listener = (tabId: number, changeInfo: chrome.tabs.TabChangeInfo) => {
        if (tabId === tab.id && changeInfo.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);
          resolve();
        }
      };
      chrome.tabs.onUpdated.addListener(listener);
      
      // Timeout after 30 seconds
      setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }, 30000);
    });

    // Wait a bit more for dynamic content
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Extract content using content script
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id! },
      func: extractContent,
    });

    const content = results[0]?.result;

    if (content && content.length > 100) {
      // Upload to server
      await api.uploadContent(item.id, {
        content,
        extraction_source: 'chrome_extension',
      });
      console.log(`✓ Successfully extracted and uploaded content for item ${item.id}`);
    } else {
      console.warn(`✗ Insufficient content extracted for item ${item.id}`);
    }

    // Close the tab
    await chrome.tabs.remove(tab.id!);
  } catch (error) {
    console.error(`Error processing item ${item.id}:`, error);
  }
}

// Content extraction function (runs in page context)
function extractContent(): string {
  // Use Readability if available, otherwise fallback to simple extraction
  try {
    // @ts-ignore - Readability will be injected
    if (typeof Readability !== 'undefined') {
      // @ts-ignore
      const article = new Readability(document.cloneNode(true)).parse();
      if (article && article.textContent) {
        return `# ${article.title}\n\n${article.textContent}`;
      }
    }
  } catch (e) {
    console.error('Readability extraction failed:', e);
  }

  // Fallback: extract main content
  const main = document.querySelector('main, article, [role="main"]');
  const content = main ? main.textContent : document.body.textContent;
  return content?.trim() || '';
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'PROCESS_PENDING_NOW') {
    processPendingItems().then(() => {
      sendResponse({ success: true });
    }).catch((error) => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Keep channel open for async response
  }
  
  if (message.type === 'UPDATE_POLLING_SETTINGS') {
    const { enabled, intervalMinutes } = message.payload;
    if (enabled) {
      setupPollingAlarm(intervalMinutes).then(() => {
        sendResponse({ success: true });
      });
    } else {
      chrome.alarms.clear('pollPendingItems').then(() => {
        sendResponse({ success: true });
      });
    }
    return true;
  }
});

// Export for testing
export { processPendingItems, processItem };
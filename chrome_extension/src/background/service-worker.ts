import { ContentStashAPI } from '../lib/api';
import { Storage } from '../lib/storage';
import { extractYouTubeTranscript, extractVideoId, isYouTubeUrl } from '../lib/youtube-extractor';
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
    
    // Check if this is a YouTube URL
    if (isYouTubeUrl(item.url)) {
      await processYouTubeItem(item);
    } else {
      await processGenericItem(item);
    }
  } catch (error) {
    console.error(`Error processing item ${item.id}:`, error);
  }
}

// Process a YouTube video item
async function processYouTubeItem(item: SavedItem) {
  try {
    console.log(`[YouTube] Processing video: ${item.url}`);
    
    // Extract video ID from URL
    const videoId = extractVideoId(item.url!);
    if (!videoId) {
      console.error(`[YouTube] Could not extract video ID from URL: ${item.url}`);
      return;
    }
    
    console.log(`[YouTube] Extracted video ID: ${videoId}`);
    
    // Extract transcript using the YouTube extractor
    const transcript = await extractYouTubeTranscript(videoId);
    
    if (!transcript || transcript.length < 100) {
      console.warn(`[YouTube] Insufficient transcript content for item ${item.id}`);
      return;
    }
    
    console.log(`[YouTube] Successfully extracted transcript (${transcript.length} chars)`);
    
    // Upload to server
    await api.uploadContent(item.id, {
      content: transcript,
      extraction_source: 'chrome_extension_youtube',
    });
    
    console.log(`✓ [YouTube] Successfully uploaded transcript for item ${item.id}`);
  } catch (error) {
    console.error(`[YouTube] Error processing item ${item.id}:`, error);
  }
}

// Process a generic web page item
async function processGenericItem(item: SavedItem) {
  let tab: chrome.tabs.Tab | undefined;
  
  try {
    console.log(`[Generic] Processing page: ${item.url}`);
    
    // Create a new tab in the background
    tab = await chrome.tabs.create({
      url: item.url,
      active: false,
      pinned: true,
    });

    // Wait for the tab to load
    await new Promise<void>((resolve) => {
      const listener = (tabId: number, changeInfo: chrome.tabs.TabChangeInfo) => {
        if (tabId === tab!.id && changeInfo.status === 'complete') {
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

    // Call the extraction function from the content script (already injected via manifest)
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id! },
      func: () => {
        // @ts-ignore - ContentStashExtractor is injected by content-script.js
        return window.ContentStashExtractor?.extractPageContent();
      },
    });

    const content = results[0]?.result;

    if (content && content.length > 100) {
      // Upload to server
      await api.uploadContent(item.id, {
        content,
        extraction_source: 'chrome_extension',
      });
      console.log(`✓ [Generic] Successfully extracted and uploaded content for item ${item.id} (${content.length} chars)`);
    } else {
      const errorMsg = `Insufficient content extracted (${content?.length || 0} chars, minimum 100 required)`;
      console.warn(`✗ [Generic] ${errorMsg} for item ${item.id}`);
      
      // Report failure to server by uploading minimal content with error indicator
      // This allows the backend to mark the item as failed or retry with different method
      try {
        await api.uploadContent(item.id, {
          content: content || `[Extraction Failed] ${errorMsg}\n\nURL: ${item.url}`,
          extraction_source: 'chrome_extension_failed',
        });
        console.log(`✓ [Generic] Reported extraction failure to server for item ${item.id}`);
      } catch (uploadError) {
        console.error(`✗ [Generic] Failed to report extraction failure for item ${item.id}:`, uploadError);
      }
    }

    // Close the tab
    if (tab?.id) {
      await chrome.tabs.remove(tab.id);
    }
  } catch (error) {
    console.error(`[Generic] Error processing item ${item.id}:`, error);
    
    // Report the error to the server
    try {
      await api.uploadContent(item.id, {
        content: `[Extraction Error] ${error instanceof Error ? error.message : String(error)}\n\nURL: ${item.url}`,
        extraction_source: 'chrome_extension_error',
      });
      console.log(`✓ [Generic] Reported extraction error to server for item ${item.id}`);
    } catch (uploadError) {
      console.error(`✗ [Generic] Failed to report extraction error for item ${item.id}:`, uploadError);
    }
    
    // Ensure tab is closed even on error
    if (tab?.id) {
      try {
        await chrome.tabs.remove(tab.id);
      } catch (e) {
        console.error('[Generic] Error closing tab:', e);
      }
    }
  }
}

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
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
  
  // Handle YouTube extraction request from content script
  if (message.type === 'EXTRACT_YOUTUBE_FROM_TAB') {
    (async () => {
      try {
        if (!sender.tab?.id) {
          sendResponse({ success: false, error: 'No tab ID available' });
          return;
        }
        
        // Extract metadata and caption URL from MAIN world
        const results = await chrome.scripting.executeScript({
          target: { tabId: sender.tab.id },
          world: 'MAIN',
          func: extractYouTubeTranscriptFromPage,
        });
        
        const result = results[0]?.result;
        
        if (!result || !result.success) {
          sendResponse({ success: false, error: result?.error || 'Metadata extraction failed' });
          return;
        }
        
        const metadata = result.metadata;
        
        if (!metadata) {
          sendResponse({ success: false, error: 'No metadata returned' });
          return;
        }
        
        // Check if we got transcript XML from MAIN world
        const transcriptXml = result.transcriptXml;
        
        if (transcriptXml) {
          sendResponse({
            success: true,
            metadata: metadata,
            transcriptXml: transcriptXml
          });
        } else {
          sendResponse({
            success: true,
            metadata: metadata
          });
        }
        
      } catch (error) {
        console.error('YouTube extraction error:', error);
        sendResponse({
          success: false,
          error: error instanceof Error ? error.message : String(error)
        });
      }
    })();
    return true; // Keep channel open for async response
  }
  
  // DEPRECATED: YouTube transcript extraction now happens via chrome.scripting.executeScript
  // with world: "MAIN" to avoid CSP violations
  // Keeping this code commented for reference
  /*
  if (message.type === 'EXTRACT_YOUTUBE_TRANSCRIPT') {
    const { videoId } = message.payload;
    
    if (!videoId) {
      sendResponse({ success: false, error: 'No video ID provided' });
      return false;
    }
    
    // Extract transcript using privileged background context
    extractYouTubeTranscript(videoId)
      .then((transcript) => {
        sendResponse({ success: true, transcript });
      })
      .catch((error) => {
        console.error('[Background] Transcript extraction failed:', error);
        sendResponse({
          success: false,
          error: error instanceof Error ? error.message : String(error)
        });
      });
    
    return true; // Keep channel open for async response
  }
  */
});

// MAIN world extraction function - uses InnerTube API with Android client spoofing
// This function will be serialized and executed in the page context
async function extractYouTubeTranscriptFromPage(): Promise<{
  success: boolean;
  metadata?: {
    title: string;
    author: string;
    videoId: string;
    lengthSeconds: number;
    captionUrl: string | null;
  };
  transcriptXml?: string;
  error?: string;
}> {
  try {
    const playerResponse = (window as any).ytInitialPlayerResponse;
    
    if (!playerResponse?.videoDetails) {
      throw new Error('ytInitialPlayerResponse not found');
    }

    // Extract metadata
    const { title, author, videoId, lengthSeconds } = playerResponse.videoDetails;

    // Step 1: Extract INNERTUBE_API_KEY from page HTML
    const html = document.documentElement.outerHTML;
    const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":\s*"([^"]+)"/);
    
    if (!apiKeyMatch) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }
    
    const apiKey = apiKeyMatch[1];

    // Step 2: POST to InnerTube API with Android client context
    const innerTubeUrl = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;
    
    const innerTubeResponse = await fetch(innerTubeUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept-Language': 'en-US'
      },
      body: JSON.stringify({
        context: {
          client: {
            clientName: 'ANDROID',
            clientVersion: '20.10.38'
          }
        },
        videoId: videoId
      })
    });

    if (!innerTubeResponse.ok) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }

    const playerData = await innerTubeResponse.json();

    // Step 3: Extract caption tracks from InnerTube response
    const captionTracks = playerData?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    
    if (!captionTracks || captionTracks.length === 0) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }

    // Select best English track (prefer manual over auto-generated)
    let selectedTrack = null;
    for (const track of captionTracks) {
      if (track.languageCode === 'en') {
        if (!track.kind) {
          // Manual track (no kind property)
          selectedTrack = track;
          break;
        } else if (!selectedTrack) {
          // Auto-generated track (has kind property)
          selectedTrack = track;
        }
      }
    }

    if (!selectedTrack?.baseUrl) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }

    const captionUrl = selectedTrack.baseUrl;

    // Step 4: Fetch transcript XML
    const transcriptResponse = await fetch(captionUrl);

    if (!transcriptResponse.ok) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }

    const xml = await transcriptResponse.text();

    if (!xml || xml.length === 0) {
      return {
        success: true,
        metadata: { title, author, videoId, lengthSeconds, captionUrl: null }
      };
    }

    return {
      success: true,
      metadata: { title, author, videoId, lengthSeconds, captionUrl },
      transcriptXml: xml
    };

  } catch (error) {
    console.error('YouTube extraction error:', error);
    return { success: false, error: String(error) };
  }
}

// Export for testing
export { processPendingItems, processItem, processYouTubeItem, processGenericItem };
import { ContentStashAPI } from '../lib/api';
import { Storage } from '../lib/storage';
import { extractYouTubeTranscript, fetchYouTubeTranscriptXml, extractVideoId, isYouTubeUrl } from '../lib/youtube-extractor';
import type { SavedItem } from '../types';

const api = new ContentStashAPI();
const POLL_ALARM = 'pollPendingItems';
const IDLE_POLL_SECONDS = 900;
const ACTIVE_POLL_SECONDS = 10;
const WARM_POLL_SECONDS = 60;
const MAX_BACKOFF_SECONDS = 300;

let isPollingInFlight = false;
let failureBackoffSeconds = 0;

function withJitter(seconds: number): number {
  const jitter = 0.9 + Math.random() * 0.2;
  return Math.max(5, Math.round(seconds * jitter));
}

async function scheduleNextPoll(seconds: number) {
  const nextSeconds = withJitter(seconds);
  await chrome.alarms.clear(POLL_ALARM);
  await chrome.alarms.create(POLL_ALARM, {
    when: Date.now() + nextSeconds * 1000,
  });
  console.log(`Next local queue check in ${nextSeconds}s`);
}

async function ensurePollAlarmScheduled() {
  const existingAlarm = await chrome.alarms.get(POLL_ALARM);
  if (!existingAlarm) {
    await scheduleNextPoll(WARM_POLL_SECONDS);
  }
}

// Initialize on install/startup
chrome.runtime.onInstalled.addListener(async () => {
  console.log('ContentStash extension installed');
  await scheduleNextPoll(WARM_POLL_SECONDS);
});

chrome.runtime.onStartup.addListener(async () => {
  await scheduleNextPoll(WARM_POLL_SECONDS);
});

// Ensure polling is armed even if lifecycle events did not recreate the alarm.
void ensurePollAlarmScheduled();

// Handle alarm for polling
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === POLL_ALARM) {
    await processPendingItems();
  }
});

// Process pending local extraction items
async function processPendingItems() {
  if (isPollingInFlight) {
    console.log('Local queue poll already in flight, skipping duplicate trigger');
    return;
  }

  isPollingInFlight = true;

  try {
    const authState = await Storage.getAuthState();

    if (!authState.isAuthenticated || !authState.token) {
      console.log('Not authenticated, skipping polling');
      await scheduleNextPoll(IDLE_POLL_SECONDS);
      return;
    }

    api.baseUrl = authState.serverUrl || api.baseUrl;
    api.setToken(authState.token);

    const hint = await api.getPendingLocalHint();
    const hasPending = hint.pending_count > 0;

    if (!hasPending) {
      failureBackoffSeconds = 0;
      // Hint checks are lightweight; keep authenticated idle cadence warm for faster queue pickup.
      await scheduleNextPoll(Math.min(hint.recommended_poll_seconds || IDLE_POLL_SECONDS, WARM_POLL_SECONDS));
      return;
    }

    const pendingItems = await api.getPendingLocalItems();
    console.log(`Found ${pendingItems.length} items pending local extraction`);

    for (const item of pendingItems) {
      await processItem(item);
    }

    failureBackoffSeconds = 0;
    await scheduleNextPoll(Math.min(hint.recommended_poll_seconds || ACTIVE_POLL_SECONDS, ACTIVE_POLL_SECONDS));
  } catch (error) {
    console.error('Error processing pending items:', error);
    failureBackoffSeconds = failureBackoffSeconds === 0
      ? 15
      : Math.min(failureBackoffSeconds * 2, MAX_BACKOFF_SECONDS);
    await scheduleNextPoll(failureBackoffSeconds);
  } finally {
    isPollingInFlight = false;
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

async function reportExtractionFailure(
  item: SavedItem,
  errorMessage: string,
  extractionSource: 'chrome_extension_failed' | 'chrome_extension_error' = 'chrome_extension_failed'
) {
  try {
    await api.uploadContent(item.id, {
      content: `[Extraction ${extractionSource === 'chrome_extension_error' ? 'Error' : 'Failed'}] ${errorMessage}\n\nURL: ${item.url || 'unknown'}`,
      extraction_source: extractionSource,
    });
    console.log(`✓ Reported ${extractionSource} for item ${item.id}`);
  } catch (uploadError) {
    console.error(`✗ Failed to report ${extractionSource} for item ${item.id}:`, uploadError);
  }
}

// Process a YouTube video item
async function processYouTubeItem(item: SavedItem) {
  try {
    console.log(`[YouTube] Processing video: ${item.url}`);

    // Extract video ID from URL
    const videoId = extractVideoId(item.url!);
    if (!videoId) {
      const errorMsg = `Could not extract video ID from URL: ${item.url}`;
      console.error(`[YouTube] ${errorMsg}`);
      await reportExtractionFailure(item, errorMsg, 'chrome_extension_failed');
      return;
    }

    console.log(`[YouTube] Extracted video ID: ${videoId}`);

    // Extract transcript using the YouTube extractor
    const result = await extractYouTubeTranscript(videoId);

    if (!result || !result.content || result.content.length < 100) {
      const errorMsg = `Insufficient transcript content (${result?.content?.length || 0} chars, minimum 100 required)`;
      console.warn(`[YouTube] ${errorMsg} for item ${item.id}`);
      await reportExtractionFailure(item, errorMsg, 'chrome_extension_failed');
      return;
    }

    console.log(`[YouTube] Successfully extracted transcript (${result.content.length} chars)`);

    // Format source field as "YouTube | [Channel Name]"
    const source = result.channelName ? `YouTube | ${result.channelName}` : 'YouTube';

    // Upload to server
    await api.uploadContent(item.id, {
      content: result.content,
      extraction_source: 'chrome_extension_youtube',
      source: source,
    });

    console.log(`✓ [YouTube] Successfully uploaded transcript for item ${item.id} with source: ${source}`);
  } catch (error) {
    console.error(`[YouTube] Error processing item ${item.id}:`, error);
    await reportExtractionFailure(
      item,
      error instanceof Error ? error.message : String(error),
      'chrome_extension_error'
    );
  }
}

// Process a generic web page item
async function processGenericItem(item: SavedItem) {
  let tab: chrome.tabs.Tab | undefined;

  try {
    console.log(`[Generic] Processing page: ${item.url}`);

    // Check if metadata is missing (title looks like a URL)
    const needsMetadata = !item.title ||
      item.title.startsWith('http://') ||
      item.title.startsWith('https://') ||
      !item.description ||
      !item.image_url;

    if (needsMetadata) {
      console.log(`[Generic] Item ${item.id} needs metadata extraction`);
    }

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

    // Extract metadata if needed
    if (needsMetadata) {
      try {
        console.log(`[Generic] Extracting metadata for item ${item.id}`);
        const metadataResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id! },
          func: () => {
            // @ts-ignore - ContentStashExtractor is injected by content-script.js
            return window.ContentStashExtractor?.extractPageMetadata();
          },
        });

        const metadata = metadataResults[0]?.result;

        if (metadata && (metadata.title || metadata.description || metadata.image)) {
          console.log(`[Generic] Extracted metadata:`, metadata);

          // Update item with extracted metadata
          const updateData: any = {};
          if (metadata.title && metadata.title !== item.title) {
            updateData.title = metadata.title;
          }
          if (metadata.description && !item.description) {
            updateData.description = metadata.description;
          }
          if (metadata.image && !item.image_url) {
            updateData.image_url = metadata.image;
          }

          if (Object.keys(updateData).length > 0) {
            await api.updateItemMetadata(item.id, updateData);
            console.log(`✓ [Generic] Updated metadata for item ${item.id}`);
          }
        }
      } catch (metadataError) {
        console.warn(`[Generic] Failed to extract/update metadata for item ${item.id}:`, metadataError);
        // Continue with content extraction even if metadata fails
      }
    }

    // Call the extraction function from the content script (already injected via manifest)
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id! },
      func: () => {
        // @ts-ignore - ContentStashExtractor is injected by content-script.js
        return window.ContentStashExtractor?.extractPageContent();
      },
    });

    const extractionResult = results[0]?.result;
    const content = typeof extractionResult === 'string'
      ? extractionResult
      : (typeof extractionResult?.content === 'string' ? extractionResult.content : '');

    if (content && content.length > 100) {
      // Upload to server
      await api.uploadContent(item.id, {
        content,
        extraction_source: 'chrome_extension',
      });
      console.log(`✓ [Generic] Successfully extracted and uploaded content for item ${item.id} (${content.length} chars)`);
    } else {
      const errorMsg = `Insufficient content extracted (${content.length} chars, minimum 100 required)`;
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
        let transcriptXml = result.transcriptXml;

        // Fallback: If in-page extraction returned no transcript, try legacy background fetch (XML Only)
        if (!transcriptXml || transcriptXml.trim().length === 0) {
          console.log(`[Service Worker] In-page transcript empty for ${metadata.videoId}. Triggering legacy background fallback (Safe Fetch)...`);
          try {
            // Use the XML-only fetcher that doesn't use DOMParser (safe for Service Worker)
            const legacyResult = await fetchYouTubeTranscriptXml(metadata.videoId);
            if (legacyResult && legacyResult.transcriptXml) {
              console.log('[Service Worker] Legacy background extraction successful');
              transcriptXml = legacyResult.transcriptXml;
              // We can also update channel name if available
              if (legacyResult.channelName) {
                metadata.channelName = legacyResult.channelName;
              }
            }
          } catch (err) {
            console.error('[Service Worker] Legacy background fallback failed:', err);
          }
        }

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
    channelName?: string;
    description?: string;
  };
  transcriptXml?: string;
  error?: string;
}> {
  try {
    // Step 1: Extract Video ID from URL (Primary Source for correct navigation)
    const url = window.location.href;
    const videoIdMatch = url.match(/[?&]v=([^&]+)/);
    const videoId = videoIdMatch ? videoIdMatch[1] : null;

    if (!videoId) {
      throw new Error('Could not extract video ID from URL');
    }

    // Step 2: Extract INNERTUBE_API_KEY from page HTML
    const html = document.documentElement.outerHTML;
    const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":\s*"([^"]+)"/);

    if (!apiKeyMatch) {
      throw new Error('Could not extract INNERTUBE_API_KEY');
    }

    const apiKey = apiKeyMatch[1];
    let playerData;



    // HYBRID APPROACH: Prioritize InnerTube API for robust transcripts
    // We only use Global data as a fallback if InnerTube fails.
    const globalResponse = (window as any).ytInitialPlayerResponse;
    const globalVideoId = globalResponse?.videoDetails?.videoId;

    console.log('[ContentStash] Fetching fresh metadata/captions from InnerTube API (Robust Path)');

    try {
      // Step 3: POST to InnerTube API with Android client context (Android provides most robust URLs)
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

      if (innerTubeResponse.ok) {
        playerData = await innerTubeResponse.json();
        console.log('[ContentStash] Successfully fetched fresh data from InnerTube API');
      } else {
        console.warn(`[ContentStash] InnerTube API failed (Status: ${innerTubeResponse.status}). Falling back to Global.`);
      }
    } catch (e) {
      console.warn('[ContentStash] Error fetching from InnerTube API. Falling back to Global.', e);
    }

    // Fallback to Global if InnerTube failed but Global matches
    if (!playerData && globalVideoId === videoId) {
      console.log('[ContentStash] Using global ytInitialPlayerResponse as fallback source');
      playerData = globalResponse;
    }

    // Extract metadata from player data
    const videoDetails = playerData?.videoDetails;
    if (!videoDetails) {
      throw new Error('No videoDetails found in any source (InnerTube or Global)');
    }

    const { title, author, lengthSeconds, shortDescription } = videoDetails;
    const channelName = author;

    // Initialize transcript variables
    let transcriptXml: string | null = null;
    let selectedTrack = null;

    // Helper for fetching transcript with unsigned fallback
    const fetchTranscriptWithFallback = async (baseUrl: string, videoId: string) => {
      console.log(`[ContentStash] Fetching transcript from: ${baseUrl.substring(0, 150)}...`);
      try {
        const resp = await fetch(baseUrl);
        const status = resp.status;
        const contentType = resp.headers.get('content-type') || '';
        const finalUrl = resp.url;
        console.log(`[ContentStash] Response: ${status}, Content-Type: ${contentType}`);

        // Check if we were redirected to an error page or got HTML instead of XML
        const isErrorPage = finalUrl.includes('/error') || finalUrl.includes('/upsell');
        const isHtml = contentType.includes('text/html');

        if (resp.ok && !isErrorPage && !isHtml) {
          let text = await resp.text();
          // Check if it's actually XML (should start with <)
          if (text && text.trim().startsWith('<')) {
            console.log(`[ContentStash] Fetched valid XML. Length: ${text.length} chars.`);
            return text;
          }
          console.warn(`[ContentStash] Response body is empty or not XML (Length: ${text?.length || 0}).`);
        } else {
          console.warn(`[ContentStash] Signed URL failed (Status: ${status}, Type: ${contentType}, ErrorPage: ${isErrorPage}).`);
        }

        // Try unsigned fallback
        console.log(`[ContentStash] Trying unsigned fallback for video: ${videoId}`);
        const fallbacks = [
          `https://www.youtube.com/api/timedtext?v=${videoId}&lang=en&fmt=srv3`,
          `https://www.youtube.com/api/timedtext?v=${videoId}&lang=en`
        ];

        for (const url of fallbacks) {
          try {
            console.log(`[ContentStash] Fetching fallback: ${url}`);
            const fallbackResp = await fetch(url);
            const fbStatus = fallbackResp.status;
            const fbContentType = fallbackResp.headers.get('content-type') || '';
            console.log(`[ContentStash] Fallback response: ${fbStatus}, Content-Type: ${fbContentType}`);

            if (fallbackResp.ok && !fbContentType.includes('html')) {
              const fallbackText = await fallbackResp.text();
              if (fallbackText && fallbackText.trim().startsWith('<')) {
                console.log(`[ContentStash] Fallback successful: ${fallbackText.length} chars.`);
                return fallbackText;
              } else {
                console.warn(`[ContentStash] Fallback returned invalid XML or empty body`);
              }
            } else {
              console.warn(`[ContentStash] Fallback failed validation (Status: ${fbStatus}, HTML: ${fbContentType.includes('html')})`);
            }
          } catch (e) {
            console.warn('[ContentStash] Fallback attempt error:', e);
          }
        }
      } catch (e) {
        console.warn('[ContentStash] Fetch error:', e);
      }
      return null;
    };

    // Try to get transcript from available tracks (Global or API)
    if (!transcriptXml) {
      const captionTracks = playerData?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
      if (captionTracks && captionTracks.length > 0) {
        // Filter and sort English tracks (Manual first, then ASR)
        const englishTracks = captionTracks.filter((t: any) => t.languageCode === 'en')
          .sort((a: any, b: any) => {
            const aIsAsr = a.kind === 'asr';
            const bIsAsr = b.kind === 'asr';
            if (aIsAsr && !bIsAsr) return 1;
            if (!aIsAsr && bIsAsr) return -1;
            return 0;
          });

        for (const track of englishTracks) {
          const trackName = track.name?.simpleText || track.vssId || 'English';
          console.log(`[ContentStash] (API/Global) Trying track: ${trackName} (Kind: ${track.kind || 'manual'})`);
          if (track.baseUrl) {
            const text = await fetchTranscriptWithFallback(track.baseUrl, videoId);
            if (text) {
              transcriptXml = text;
              selectedTrack = track;
              break; // Found working transcript
            }
          }
        }
      }
    }

    return {
      success: true,
      metadata: {
        title,
        author,
        videoId,
        lengthSeconds: parseInt(lengthSeconds),
        captionUrl: selectedTrack?.baseUrl || null,
        channelName,
        description: shortDescription
      },
      transcriptXml: transcriptXml || undefined
    };

  } catch (error) {
    console.error('YouTube extraction error:', error);
    return { success: false, error: String(error) };
  }
}

// Export for testing
export { processPendingItems, processItem, processYouTubeItem, processGenericItem };

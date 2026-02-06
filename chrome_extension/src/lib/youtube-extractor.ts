/**
 * YouTube Transcript Extractor
 * 
 * Extracts transcripts from YouTube videos by:
 * 1. Fetching the YouTube watch page HTML
 * 2. Parsing ytInitialPlayerResponse from the page source
 * 3. Extracting caption track URL
 * 4. Fetching and parsing the XML transcript
 * 5. Formatting as Markdown with timestamps
 */

export interface CaptionTrack {
  baseUrl: string;
  name: { simpleText: string };
  vssId: string;
  languageCode: string;
  kind?: string;
}

export interface TranscriptSegment {
  start: number;
  duration: number;
  text: string;
}

export interface YouTubeExtractionResult {
  content: string;
  channelName?: string;
}

/**
 * Extract YouTube transcript from a video ID
 * @param videoId - The YouTube video ID (e.g., "dQw4w9WgXcQ")
 * @returns Object with formatted transcript and channel name, or null if extraction fails
 */
export async function extractYouTubeTranscript(videoId: string): Promise<YouTubeExtractionResult | null> {
  try {
    console.log('='.repeat(80));
    console.log(`[YouTube Extractor] EXTRACTION PATH: youtube-extractor.ts`);
    console.log(`[YouTube Extractor] Starting extraction for video: ${videoId}`);
    console.log('='.repeat(80));

    // Step 1: Fetch the YouTube watch page
    const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
    const response = await fetch(watchUrl);

    if (!response.ok) {
      console.error(`[YouTube Extractor] Failed to fetch page: ${response.status}`);
      return null;
    }

    const html = await response.text();

    // Step 2: Extract ytInitialPlayerResponse from the page
    const playerResponse = extractPlayerResponse(html);
    if (!playerResponse) {
      console.error('[YouTube Extractor] Could not find ytInitialPlayerResponse');
      return null;
    }

    // Step 3: Get video metadata
    const videoDetails = playerResponse.videoDetails;
    const title = videoDetails?.title || 'Unknown Title';
    const author = videoDetails?.author || 'Unknown Channel';
    const lengthSeconds = videoDetails?.lengthSeconds || 0;

    console.log(`[YouTube Extractor] Video: "${title}" by ${author}`);

    // Step 4: Find caption tracks
    const captionTracks = playerResponse.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    if (!captionTracks || captionTracks.length === 0) {
      console.error('[YouTube Extractor] No caption tracks found');
      return null;
    }

    // Step 5: Select all English tracks
    const englishTracks = findAllEnglishTracks(captionTracks);
    if (englishTracks.length === 0) {
      console.error('[YouTube Extractor] No English caption tracks found');
      return null;
    }

    let transcriptXml: string | null = null;

    // Try each track until one works
    for (const track of englishTracks) {
      console.log(`[YouTube Extractor] Trying track: ${track.name.simpleText} (${track.kind || 'manual'})`);
      transcriptXml = await fetchTranscriptXml(track.baseUrl, videoId);
      if (transcriptXml) {
        console.log(`[YouTube Extractor] Successfully fetched XML from track: ${track.name.simpleText}`);
        break;
      } else {
        console.warn(`[YouTube Extractor] Failed to fetch content from track: ${track.name.simpleText}`);
      }
    }

    if (!transcriptXml) {
      console.warn('[YouTube Extractor] All English tracks failed to return content');
      return null;
    }

    // Step 7: Parse and format the transcript
    const segments = parseTranscriptXml(transcriptXml);
    if (segments.length === 0) {
      console.error('[YouTube Extractor] No transcript segments found');
      return null;
    }

    // Step 8: Format as Markdown
    const markdown = formatTranscriptAsMarkdown(title, author, videoId, lengthSeconds, segments);

    console.log(`[YouTube Extractor] Successfully extracted ${segments.length} segments`);
    return {
      content: markdown,
      channelName: author
    };

  } catch (error) {
    console.error('[YouTube Extractor] Error during extraction:', error);
    return null;
  }
}

// ... (existing code)

/**
 * Fetch the transcript XML from a video ID (Raw XML result for Service Worker)
 */
export async function fetchYouTubeTranscriptXml(videoId: string): Promise<{ transcriptXml: string; channelName?: string; } | null> {
  try {
    console.log(`[YouTube Extractor] Starting XML fetch for video: ${videoId}`);

    // Step 1: Fetch the YouTube watch page
    const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
    const response = await fetch(watchUrl);

    if (!response.ok) {
      console.error(`[YouTube Extractor] Failed to fetch page: ${response.status}`);
      return null;
    }

    const html = await response.text();

    // Step 2: Extract ytInitialPlayerResponse from the page
    const playerResponse = extractPlayerResponse(html);
    if (!playerResponse) {
      console.error('[YouTube Extractor] Could not find ytInitialPlayerResponse');
      return null;
    }

    // Step 3: Get video metadata
    const videoDetails = playerResponse.videoDetails;
    const author = videoDetails?.author || 'Unknown Channel';

    // Step 4: Find caption tracks
    const captionTracks = playerResponse.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    if (!captionTracks || captionTracks.length === 0) {
      console.error('[YouTube Extractor] No caption tracks found');
      return null;
    }

    // Step 5: Select all English tracks (manual preferred)
    const englishTracks = findAllEnglishTracks(captionTracks);
    if (englishTracks.length === 0) {
      console.error('[YouTube Extractor] No English caption tracks found');
      return null;
    }

    let transcriptXml: string | null = null;

    // Try each track until one works
    for (const track of englishTracks) {
      console.log(`[YouTube Extractor] Trying track: ${track.name.simpleText} (${track.kind || 'manual'})`);
      transcriptXml = await fetchTranscriptXml(track.baseUrl, videoId);
      if (transcriptXml) {
        console.log(`[YouTube Extractor] Successfully fetched XML from track: ${track.name.simpleText}`);
        break;
      } else {
        console.warn(`[YouTube Extractor] Failed to fetch content from track: ${track.name.simpleText}`);
      }
    }

    if (!transcriptXml) {
      console.warn('[YouTube Extractor] All English tracks failed to return content');
      return null;
    }

    return {
      transcriptXml,
      channelName: author
    };

  } catch (error) {
    console.error('[YouTube Extractor] Error during XML fetch:', error);
    return null;
  }
}

/**
 * Extract ytInitialPlayerResponse JSON from HTML
 */
function extractPlayerResponse(html: string): any {
  // Try multiple patterns to find the player response
  const patterns = [
    /var ytInitialPlayerResponse\s*=\s*({.+?});/,
    /ytInitialPlayerResponse\s*=\s*({.+?});/,
    /"ytInitialPlayerResponse"\s*:\s*({.+?})(?:,|$)/,
  ];

  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match && match[1]) {
      try {
        return JSON.parse(match[1]);
      } catch (e) {
        console.warn('[YouTube Extractor] Failed to parse player response with pattern:', pattern);
        continue;
      }
    }
  }

  return null;
}

/**
 * Find all English caption tracks, sorted by quality (Manual > Auto)
 */
function findAllEnglishTracks(tracks: CaptionTrack[]): CaptionTrack[] {
  const manualEnglish = tracks.filter(
    t => t.languageCode === 'en' && t.kind !== 'asr'
  );

  const autoEnglish = tracks.filter(t => t.languageCode === 'en' && t.kind === 'asr');

  // Return manual first, then auto
  return [...manualEnglish, ...autoEnglish];
}

/**
 * Fetch the transcript XML from the caption URL
 */
async function fetchTranscriptXml(baseUrl: string, videoId?: string): Promise<string | null> {
  try {
    console.log(`[YouTube Extractor] Fetching transcript from: ${baseUrl.substring(0, 150)}...`);
    const response = await fetch(baseUrl);

    const status = response.status;
    const contentType = response.headers.get('content-type') || '';
    const finalUrl = response.url;
    console.log(`[YouTube Extractor] Response: ${status}, Content-Type: ${contentType}`);

    // Check if we were redirected to an error page or got HTML instead of XML
    const isErrorPage = finalUrl.includes('/error') || finalUrl.includes('/upsell');
    const isHtml = contentType.includes('text/html');

    if (!response.ok || isErrorPage || (isHtml && status === 200)) {
      console.warn(`[YouTube Extractor] Signed URL failed (Status: ${status}, Type: ${contentType}, ErrorPage: ${isErrorPage}).`);
    } else {
      let text = await response.text();
      // Check if it's actually XML (should start with <)
      if (text && text.trim().startsWith('<')) {
        console.log(`[YouTube Extractor] Fetched valid XML. Length: ${text.length} chars.`);
        return text;
      }
      console.warn(`[YouTube Extractor] Response body is empty or not XML (Length: ${text?.length || 0}).`);
    }

    // If signed URL failed or was hidden/robotic, try unsigned fallback if we have a videoId
    if (videoId) {
      console.log(`[YouTube Extractor] Trying unsigned fallback for video: ${videoId}`);
      // Try multiple fallback formats
      const fallbacks = [
        `https://www.youtube.com/api/timedtext?v=${videoId}&lang=en&fmt=srv3`,
        `https://www.youtube.com/api/timedtext?v=${videoId}&lang=en`
      ];

      for (const url of fallbacks) {
        try {
          console.log(`[YouTube Extractor] Fetching fallback: ${url}`);
          const fallbackResp = await fetch(url);
          if (fallbackResp.ok && !(fallbackResp.headers.get('content-type') || '').includes('html')) {
            const fallbackText = await fallbackResp.text();
            if (fallbackText && fallbackText.trim().startsWith('<')) {
              console.log(`[YouTube Extractor] Fallback successful: ${fallbackText.length} chars.`);
              return fallbackText;
            }
          }
        } catch (e) {
          console.warn(`[YouTube Extractor] Fallback attempt failed:`, e);
        }
      }
    }

    return null;
  } catch (error) {
    console.warn('[YouTube Extractor] Error fetching transcript XML:', error);
    return null;
  }
}

/**
 * Parse transcript XML into segments.
 * Robustly handles multiple YouTube formats:
 * - <text start="1.2" dur="0.5"> format (seconds)
 * - <p t="1200" d="500"> format (milliseconds)
 */
export function parseTranscriptXml(xml: string): TranscriptSegment[] {
  const segments: TranscriptSegment[] = [];

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');

    // YouTube transcripts can use <text> or <p> tags
    const nodes = doc.querySelectorAll('text, p');

    nodes.forEach((node) => {
      // Handle <text start="..."> (seconds) or <p t="..."> (milliseconds)
      const startAttr = node.getAttribute('start') || node.getAttribute('t');
      const durAttr = node.getAttribute('dur') || node.getAttribute('d');
      const text = decodeHtmlEntities(node.textContent || '');

      if (startAttr !== null && text.trim()) {
        // If it came from 't' attribute, it's milliseconds
        const isMs = node.hasAttribute('t');
        const start = parseFloat(startAttr) / (isMs ? 1000 : 1);
        const duration = durAttr ? parseFloat(durAttr) / (isMs ? 1000 : 1) : 0;

        // Replace internal newlines and multiple spaces with single space, then trim
        const cleanText = text.replace(/\s+/g, ' ').trim();

        segments.push({ start, duration, text: cleanText });
      }
    });

    if (segments.length > 0) {
      console.log(`[YouTube Extractor] Successfully parsed ${segments.length} segments.`);
    }
  } catch (error) {
    console.error('[YouTube Extractor] Error parsing XML:', error);
  }

  return segments;
}

/**
 * Decode HTML entities in transcript text
 */
function decodeHtmlEntities(text: string): string {
  const textarea = document.createElement('textarea');
  textarea.innerHTML = text;
  return textarea.value;
}

/**
 * Format the transcript as plain text paragraphs (NO metadata header)
 * Metadata should be sent separately when uploading to backend
 */
function formatTranscriptAsMarkdown(
  _title: string,
  _author: string,
  _videoId: string,
  _lengthSeconds: number,
  segments: TranscriptSegment[]
): string {
  const lines: string[] = [];

  // Group segments into paragraphs (NO metadata header - matches server-side behavior)
  let currentParagraph: string[] = [];
  let lastEndTime = 0;

  for (const segment of segments) {
    // Skip empty segments entirely - don't process them at all
    if (!segment.text) {
      continue;
    }

    const timeSinceLastSegment = segment.start - lastEndTime;

    // Start a new paragraph if:
    // 1. This is the first segment
    // 2. There's a pause > 2 seconds
    // 3. Current paragraph is getting too long (> 500 chars)
    // Match server-side logic: >2 second gap OR >500 chars
    const currentLength = currentParagraph.join(' ').length;
    const shouldStartNewParagraph =
      currentParagraph.length === 0 ||
      timeSinceLastSegment > 2.0 ||
      currentLength > 500;

    if (shouldStartNewParagraph && currentParagraph.length > 0) {
      const paragraphText = currentParagraph.join(' ');
      lines.push(paragraphText);
      lines.push('');
      currentParagraph = [];
    }

    // Add text to paragraph and update last end time
    currentParagraph.push(segment.text);
    lastEndTime = segment.start + segment.duration;
  }

  // Write out the final paragraph
  if (currentParagraph.length > 0) {
    const paragraphText = currentParagraph.join(' ');
    lines.push(paragraphText);
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * Extract video ID from a YouTube URL
 * @param url - YouTube URL (various formats supported)
 * @returns Video ID or null if not found
 */
export function extractVideoId(url: string): string | null {
  try {
    const urlObj = new URL(url);

    // Standard watch URL: youtube.com/watch?v=VIDEO_ID
    if (urlObj.hostname.includes('youtube.com') && urlObj.pathname === '/watch') {
      return urlObj.searchParams.get('v');
    }

    // Short URL: youtu.be/VIDEO_ID
    if (urlObj.hostname === 'youtu.be') {
      return urlObj.pathname.slice(1);
    }

    // Embed URL: youtube.com/embed/VIDEO_ID
    if (urlObj.hostname.includes('youtube.com') && urlObj.pathname.startsWith('/embed/')) {
      return urlObj.pathname.split('/')[2];
    }

    return null;
  } catch (error) {
    console.error('[YouTube Extractor] Error parsing URL:', error);
    return null;
  }
}

/**
 * Check if a URL is a YouTube URL
 */
export function isYouTubeUrl(url: string): boolean {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.includes('youtube.com') || urlObj.hostname === 'youtu.be';
  } catch {
    return false;
  }
}
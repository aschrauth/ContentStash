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

interface CaptionTrack {
  baseUrl: string;
  name: { simpleText: string };
  vssId: string;
  languageCode: string;
  kind?: string;
}

interface TranscriptSegment {
  start: number;
  duration: number;
  text: string;
}

/**
 * Extract YouTube transcript from a video ID
 * @param videoId - The YouTube video ID (e.g., "dQw4w9WgXcQ")
 * @returns Formatted transcript as Markdown, or null if extraction fails
 */
export async function extractYouTubeTranscript(videoId: string): Promise<string | null> {
  try {
    console.log(`[YouTube Extractor] Starting extraction for video: ${videoId}`);
    
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
    
    // Step 5: Select best English track (prefer manual over auto-generated)
    const bestTrack = findBestEnglishTrack(captionTracks);
    if (!bestTrack) {
      console.error('[YouTube Extractor] No English caption track found');
      return null;
    }
    
    console.log(`[YouTube Extractor] Using track: ${bestTrack.name.simpleText} (${bestTrack.languageCode})`);
    
    // Step 6: Fetch the transcript XML
    const transcriptXml = await fetchTranscriptXml(bestTrack.baseUrl);
    if (!transcriptXml) {
      console.error('[YouTube Extractor] Failed to fetch transcript XML');
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
    return markdown;
    
  } catch (error) {
    console.error('[YouTube Extractor] Error during extraction:', error);
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
 * Find the best English caption track
 * Prioritizes manual captions over auto-generated
 */
function findBestEnglishTrack(tracks: CaptionTrack[]): CaptionTrack | null {
  // First, try to find manual English captions
  const manualEnglish = tracks.find(
    t => t.languageCode === 'en' && t.kind !== 'asr'
  );
  
  if (manualEnglish) {
    return manualEnglish;
  }
  
  // Fallback to auto-generated English captions
  const autoEnglish = tracks.find(t => t.languageCode === 'en');
  
  return autoEnglish || null;
}

/**
 * Fetch the transcript XML from the caption URL
 */
async function fetchTranscriptXml(baseUrl: string): Promise<string | null> {
  try {
    const response = await fetch(baseUrl);
    if (!response.ok) {
      console.error(`[YouTube Extractor] Failed to fetch transcript: ${response.status}`);
      return null;
    }
    return await response.text();
  } catch (error) {
    console.error('[YouTube Extractor] Error fetching transcript XML:', error);
    return null;
  }
}

/**
 * Parse transcript XML into segments
 */
function parseTranscriptXml(xml: string): TranscriptSegment[] {
  const segments: TranscriptSegment[] = [];
  
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    
    const textNodes = doc.querySelectorAll('text');
    
    textNodes.forEach(node => {
      const start = parseFloat(node.getAttribute('start') || '0');
      const duration = parseFloat(node.getAttribute('dur') || '0');
      const text = decodeHtmlEntities(node.textContent || '');
      
      if (text.trim()) {
        segments.push({ start, duration, text: text.trim() });
      }
    });
    
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
 * Format seconds as HH:MM:SS or MM:SS
 */
function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format the transcript as Markdown with metadata and timestamps
 */
function formatTranscriptAsMarkdown(
  title: string,
  author: string,
  videoId: string,
  lengthSeconds: number,
  segments: TranscriptSegment[]
): string {
  const lines: string[] = [];
  
  // Add metadata header
  lines.push(`# ${title}`);
  lines.push('');
  lines.push(`**Channel:** ${author}`);
  lines.push(`**Video ID:** ${videoId}`);
  lines.push(`**Duration:** ${formatTimestamp(lengthSeconds)}`);
  lines.push(`**URL:** https://www.youtube.com/watch?v=${videoId}`);
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('## Transcript');
  lines.push('');
  
  // Group segments into paragraphs
  let currentParagraph: string[] = [];
  let paragraphStartTime = 0;
  let lastEndTime = 0;
  
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const timeSinceLastSegment = segment.start - lastEndTime;
    
    // Start a new paragraph if:
    // 1. This is the first segment
    // 2. There's a pause > 2 seconds
    // 3. Current paragraph is getting too long (> 500 chars)
    const shouldStartNewParagraph = 
      currentParagraph.length === 0 ||
      timeSinceLastSegment > 2.0 ||
      currentParagraph.join(' ').length > 500;
    
    if (shouldStartNewParagraph && currentParagraph.length > 0) {
      // Write out the current paragraph with timestamp
      const timestamp = formatTimestamp(paragraphStartTime);
      lines.push(`**[${timestamp}]** ${currentParagraph.join(' ')}`);
      lines.push('');
      currentParagraph = [];
    }
    
    if (currentParagraph.length === 0) {
      paragraphStartTime = segment.start;
    }
    
    currentParagraph.push(segment.text);
    lastEndTime = segment.start + segment.duration;
  }
  
  // Write out the final paragraph
  if (currentParagraph.length > 0) {
    const timestamp = formatTimestamp(paragraphStartTime);
    lines.push(`**[${timestamp}]** ${currentParagraph.join(' ')}`);
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
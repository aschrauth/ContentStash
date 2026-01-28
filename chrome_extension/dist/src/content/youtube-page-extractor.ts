/**
 * YouTube Page Context Extractor
 * 
 * This script is designed to be injected into the MAIN world context of YouTube pages.
 * It has access to window.ytInitialPlayerResponse and can extract transcripts using
 * the user's browser session and residential IP, bypassing cloud server restrictions.
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

interface ExtractionResult {
  success: boolean;
  content?: string;
  channelName?: string;
  error?: string;
}

/**
 * Main extraction function that runs in the page's MAIN world context
 * This function has access to window.ytInitialPlayerResponse
 */
export async function extractYouTubeTranscriptFromPage(): Promise<ExtractionResult> {
  try {
    console.log('[YouTube Page Extractor] Starting extraction in MAIN world');
    
    // Access the YouTube player response from the page's global scope
    const playerResponse = (window as any).ytInitialPlayerResponse;
    
    if (!playerResponse) {
      console.error('[YouTube Page Extractor] ytInitialPlayerResponse not found');
      return {
        success: false,
        error: 'ytInitialPlayerResponse not available on page'
      };
    }
    
    // Extract video metadata
    const videoDetails = playerResponse.videoDetails;
    if (!videoDetails) {
      return {
        success: false,
        error: 'Video details not found in player response'
      };
    }
    
    const title = videoDetails.title || 'Unknown Title';
    const author = videoDetails.author || 'Unknown Channel';
    const videoId = videoDetails.videoId || '';
    const lengthSeconds = parseInt(videoDetails.lengthSeconds || '0');
    
    console.log(`[YouTube Page Extractor] Video: "${title}" by ${author}`);
    
    // Extract caption tracks
    const captionTracks = playerResponse.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    
    if (!captionTracks || captionTracks.length === 0) {
      console.warn('[YouTube Page Extractor] No caption tracks found');
      // Return metadata-only content
      return {
        success: true,
        content: formatMetadataOnly(title, author, videoId, lengthSeconds),
        channelName: author
      };
    }
    
    // Find the best English track (prefer manual over auto-generated)
    const bestTrack = findBestEnglishTrack(captionTracks);
    
    if (!bestTrack) {
      console.warn('[YouTube Page Extractor] No English caption track found');
      return {
        success: true,
        content: formatMetadataOnly(title, author, videoId, lengthSeconds),
        channelName: author
      };
    }
    
    console.log(`[YouTube Page Extractor] Using track: ${bestTrack.name.simpleText} (${bestTrack.languageCode})`);
    
    // Fetch the transcript XML using the user's session
    const transcriptXml = await fetchTranscriptXml(bestTrack.baseUrl);
    
    if (!transcriptXml) {
      console.error('[YouTube Page Extractor] Failed to fetch transcript XML');
      return {
        success: true,
        content: formatMetadataOnly(title, author, videoId, lengthSeconds),
        channelName: author
      };
    }
    
    // Parse the XML into segments
    const segments = parseTranscriptXml(transcriptXml);
    
    if (segments.length === 0) {
      console.error('[YouTube Page Extractor] No transcript segments found');
      return {
        success: true,
        content: formatMetadataOnly(title, author, videoId, lengthSeconds),
        channelName: author
      };
    }
    
    // Format as Markdown
    const markdown = formatTranscriptAsMarkdown(title, author, videoId, lengthSeconds, segments);
    
    console.log(`[YouTube Page Extractor] Successfully extracted ${segments.length} segments`);
    
    return {
      success: true,
      content: markdown,
      channelName: author
    };
    
  } catch (error) {
    console.error('[YouTube Page Extractor] Error during extraction:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error)
    };
  }
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
 * This runs in the user's browser context, so it inherits their session/cookies
 */
async function fetchTranscriptXml(baseUrl: string): Promise<string | null> {
  try {
    const response = await fetch(baseUrl);
    if (!response.ok) {
      console.error(`[YouTube Page Extractor] Failed to fetch transcript: ${response.status}`);
      return null;
    }
    return await response.text();
  } catch (error) {
    console.error('[YouTube Page Extractor] Error fetching transcript XML:', error);
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
    console.error('[YouTube Page Extractor] Error parsing XML:', error);
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
 * Format metadata-only content when transcript is unavailable
 */
function formatMetadataOnly(
  title: string,
  author: string,
  videoId: string,
  lengthSeconds: number
): string {
  const lines: string[] = [];
  
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
  lines.push('[Transcript not available or extraction failed]');
  lines.push('');
  
  return lines.join('\n');
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
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
    console.log('='.repeat(80));
    console.log('[Page Extractor] EXTRACTION PATH: youtube-page-extractor.ts (MAIN world)');
    console.log('[YouTube Page Extractor] Starting extraction in MAIN world');
    console.log('='.repeat(80));
    
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
    console.log('[Page Extractor] Parsing transcript XML, length:', xml.length);
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    
    const textNodes = doc.querySelectorAll('text');
    console.log('[Page Extractor] Found text nodes:', textNodes.length);
    
    textNodes.forEach((node, index) => {
      const start = parseFloat(node.getAttribute('start') || '0');
      const duration = parseFloat(node.getAttribute('dur') || '0');
      const text = decodeHtmlEntities(node.textContent || '');
      
      // Log first 3 segments in detail
      if (index < 3) {
        console.log(`[Page Extractor] Segment ${index} RAW text:`, JSON.stringify(text));
        console.log(`[Page Extractor] Segment ${index} has newlines:`, text.includes('\n'));
      }
      
      if (text.trim()) {
        // Replace internal newlines and multiple spaces with single space, then trim
        // This matches server-side .strip() behavior which removes ALL whitespace including newlines
        const cleanText = text.replace(/\s+/g, ' ').trim();
        
        // Log first 3 segments after cleaning
        if (index < 3) {
          console.log(`[Page Extractor] Segment ${index} AFTER normalization:`, JSON.stringify(cleanText));
          console.log(`[Page Extractor] Segment ${index} still has newlines:`, cleanText.includes('\n'));
        }
        
        segments.push({ start, duration, text: cleanText });
      }
    });
    
    console.log('[Page Extractor] Total segments parsed:', segments.length);
    
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
 * Format metadata-only content when transcript is unavailable
 * Returns just a placeholder message (NO metadata header)
 */
function formatMetadataOnly(
  _title: string,
  _author: string,
  _videoId: string,
  _lengthSeconds: number
): string {
  return '[Transcript not available or extraction failed]';
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
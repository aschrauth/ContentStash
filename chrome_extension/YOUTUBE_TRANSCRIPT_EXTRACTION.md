# YouTube Transcript Extraction

## Overview

This document describes the successful implementation of YouTube transcript extraction using YouTube's internal InnerTube API with Android client spoofing. This approach bypasses bot detection and reliably extracts transcripts from YouTube videos.

## How It Works

The extraction process follows these steps:

### 1. Extract INNERTUBE_API_KEY from Page HTML
The YouTube page HTML contains the InnerTube API key needed to make authenticated requests:
```javascript
const html = document.documentElement.outerHTML;
const apiKeyMatch = html.match(/"INNERTUBE_API_KEY":\s*"([^"]+)"/);
const apiKey = apiKeyMatch[1];
```

### 2. POST to InnerTube API with Android Client Context
We make a POST request to YouTube's internal InnerTube API, spoofing an Android client to bypass bot detection:
```javascript
const innerTubeUrl = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;

const response = await fetch(innerTubeUrl, {
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
```

### 3. Extract Caption URLs from InnerTube Response
The InnerTube API response contains caption track information:
```javascript
const playerData = await response.json();
const captionTracks = playerData?.captions?.playerCaptionsTracklistRenderer?.captionTracks;

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

const captionUrl = selectedTrack.baseUrl;
```

### 4. Fetch Transcript XML
Using the caption URL from the InnerTube response, we fetch the transcript XML:
```javascript
const transcriptResponse = await fetch(captionUrl);
const xml = await transcriptResponse.text();
```

### 5. Parse Transcript XML
The transcript XML uses `<p>` tags with `t` (time in milliseconds) and `d` (duration) attributes:
```xml
<transcript>
  <p t="0" d="2000">Hello world</p>
  <p t="2000" d="3000">This is a transcript</p>
</transcript>
```

Parse the XML:
```javascript
const parser = new DOMParser();
const xmlDoc = parser.parseFromString(xml, 'text/xml');
const textElements = xmlDoc.querySelectorAll('p');

for (const element of Array.from(textElements)) {
  const start = element.getAttribute('t'); // time in milliseconds
  const text = element.textContent;
  
  if (start && text) {
    const seconds = parseFloat(start) / 1000; // Convert ms to seconds
    const time = formatTimestamp(seconds);
    transcriptLines.push({ time, text: text.trim() });
  }
}
```

## Why This Works

### Android Client Spoofing
- YouTube's bot detection is less strict for mobile clients
- The Android client context bypasses many anti-scraping measures
- This is the same approach used by the proven `youtube-transcript-api` Python library

### InnerTube API
- InnerTube is YouTube's internal API used by their own clients
- It's more stable and reliable than public APIs
- Provides direct access to caption data without workarounds

### MAIN World Execution
- The script executes in the page's MAIN world context (not isolated content script)
- This allows access to `ytInitialPlayerResponse` and avoids CSP violations
- Fetch requests originate from the page itself, not the extension

## What Doesn't Work

### ❌ Direct Timedtext API Fetch
```javascript
// This approach is BLOCKED by YouTube
const url = `https://www.youtube.com/api/timedtext?v=${videoId}&lang=en`;
const response = await fetch(url);
// Result: 403 Forbidden or bot detection
```
**Why it fails:** YouTube detects and blocks direct API requests from extensions and scripts.

### ❌ DOM Automation
```javascript
// This approach is UNRELIABLE
const transcriptButton = document.querySelector('[aria-label="Show transcript"]');
transcriptButton?.click();
// Wait for transcript panel...
```
**Why it fails:** 
- YouTube's DOM structure changes frequently
- Timing issues with dynamic content loading
- Transcript panel may not appear or load properly
- Not suitable for background processing

### ❌ Service Worker Fetch
```javascript
// This approach is BLOCKED
// In service-worker.ts:
const response = await fetch(transcriptUrl);
// Result: CORS errors or bot detection
```
**Why it fails:** Service workers can't bypass CORS, and YouTube blocks extension requests.

### ❌ Content Script Fetch
```javascript
// This approach is BLOCKED
// In content-script.ts:
const response = await fetch(transcriptUrl);
// Result: CSP violations or bot detection
```
**Why it fails:** Content scripts run in an isolated world with CSP restrictions.

### ❌ MAIN World Direct Fetch (without InnerTube)
```javascript
// This approach is BLOCKED
// In MAIN world:
const response = await fetch(`https://www.youtube.com/api/timedtext?v=${videoId}`);
// Result: 403 Forbidden
```
**Why it fails:** Even from MAIN world, direct timedtext API requests are blocked without proper authentication.

## Technical Implementation

### File Structure
- [`chrome_extension/src/background/service-worker.ts`](src/background/service-worker.ts) - Orchestrates extraction via chrome.scripting.executeScript
- [`chrome_extension/src/content/content-script.ts`](src/content/content-script.ts) - Receives and formats transcript data
- [`chrome_extension/src/lib/youtube-extractor.ts`](src/lib/youtube-extractor.ts) - Utility functions for YouTube URLs

### Key Functions

#### `extractYouTubeTranscriptFromPage()` (MAIN world)
Executes in the page context to:
1. Access `ytInitialPlayerResponse` for metadata
2. Extract INNERTUBE_API_KEY from page HTML
3. Call InnerTube API with Android client context
4. Fetch and return transcript XML

#### `extractYouTubeContent()` (Content script)
Receives transcript XML and:
1. Parses XML using DOMParser
2. Extracts text segments with timestamps
3. Formats as markdown with metadata

### Message Flow
```
Content Script → Background Script → MAIN World Script
     ↓                                      ↓
  Request                            Execute in page
     ↓                                      ↓
Background Script ← MAIN World Script
     ↓
Content Script (receives XML)
     ↓
Parse & Format
```

## Success Metrics

- ✅ Bypasses YouTube's bot detection
- ✅ Works with both manual and auto-generated captions
- ✅ Handles videos without transcripts gracefully
- ✅ Extracts complete transcript with timestamps
- ✅ No CSP violations or CORS errors
- ✅ Based on proven methodology from youtube-transcript-api

## References

- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Python library using the same InnerTube approach
- [Chrome Extension Scripting API](https://developer.chrome.com/docs/extensions/reference/scripting/)
- [YouTube InnerTube API](https://github.com/iv-org/invidious/blob/master/docs/api.md)

## Troubleshooting

### No Transcript Available
If a video has no captions, the extraction will return metadata only. The backend can attempt alternative extraction methods.

### API Key Not Found
If `INNERTUBE_API_KEY` is not found in the page HTML, YouTube may have changed their page structure. Check the page source for the current key location.

### InnerTube API Changes
YouTube may update their InnerTube API. Monitor the `youtube-transcript-api` Python library for updates to the Android client version or API endpoints.

## Future Improvements

- Support for multiple languages (currently prioritizes English)
- Caching of transcript data to reduce API calls
- Fallback to alternative caption formats (e.g., SRT, VTT)
- Support for live stream transcripts
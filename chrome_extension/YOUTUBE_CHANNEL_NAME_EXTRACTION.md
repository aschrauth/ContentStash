# YouTube Channel Name Extraction Implementation

## Overview
Updated the Chrome extension to extract and send YouTube channel names for local extraction. The backend now receives a `source` field formatted as "YouTube | [Channel Name]" for all YouTube videos extracted via the Chrome extension.

## Changes Made

### 1. TypeScript Types (`src/types/index.ts`)
- Added `source?: string` to `UploadContentRequest` interface
- Created new `YouTubeMetadata` interface with `channelName?: string` field

### 2. YouTube Extractor (`src/lib/youtube-extractor.ts`)
- Modified `extractYouTubeTranscript()` to return `YouTubeExtractionResult` object instead of plain string
- `YouTubeExtractionResult` contains:
  - `content: string` - The formatted transcript markdown
  - `channelName?: string` - The channel name extracted from video metadata
- Channel name is extracted from the `author` field in `ytInitialPlayerResponse.videoDetails`

### 3. YouTube Page Extractor (`src/content/youtube-page-extractor.ts`)
- Updated `ExtractionResult` interface to include `channelName?: string`
- Modified `extractYouTubeTranscriptFromPage()` to return channel name in all code paths
- Channel name is extracted from `playerResponse.videoDetails.author`

### 4. Service Worker (`src/background/service-worker.ts`)
- Updated `extractYouTubeTranscriptFromPage()` function to include `channelName` in metadata
- Modified `processYouTubeItem()` to:
  - Handle the new object return type from `extractYouTubeTranscript()`
  - Format source as "YouTube | [Channel Name]" or fallback to "YouTube"
  - Send `source` field to backend via `uploadContent()` API call
- All metadata return paths now include the channel name

### 5. Content Script (`src/content/content-script.ts`)
- Updated `extractYouTubeContent()` to store channel name in window object for potential future use
- Channel name is extracted from metadata response

## Data Flow

1. **Background Polling**: Service worker polls for pending local extraction items
2. **YouTube Detection**: Identifies YouTube URLs using `isYouTubeUrl()`
3. **Transcript Extraction**: Calls `extractYouTubeTranscript(videoId)` which:
   - Fetches YouTube watch page
   - Extracts `ytInitialPlayerResponse` from page HTML
   - Gets video metadata including `author` (channel name)
   - Fetches and parses transcript XML
   - Returns object with `content` and `channelName`
4. **Source Formatting**: Formats source as "YouTube | [Channel Name]"
5. **Upload to Backend**: Sends to backend with:
   - `content`: Formatted transcript markdown
   - `extraction_source`: "chrome_extension_youtube"
   - `source`: "YouTube | [Channel Name]"

## Fallback Behavior

- If channel name cannot be extracted, source defaults to "YouTube"
- All error paths maintain backward compatibility
- Existing functionality is preserved if channel name is unavailable

## Testing

Build completed successfully with no TypeScript errors:
```bash
cd chrome_extension && npm run build
# ✓ built in 399ms
```

## Backend Integration

The backend expects:
- `source` field in the format "YouTube | [Channel Name]"
- Falls back to "YouTube" if channel name is not provided
- This field is used for source metadata and filtering

## Example Output

When a YouTube video is extracted, the backend receives:
```json
{
  "content": "# Video Title\n\n**Channel:** Channel Name\n...",
  "extraction_source": "chrome_extension_youtube",
  "source": "YouTube | Channel Name"
}
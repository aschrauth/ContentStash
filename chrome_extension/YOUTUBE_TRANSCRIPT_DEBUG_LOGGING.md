# YouTube Transcript Debug Logging Guide

## Overview

Comprehensive logging has been added to all YouTube transcript extraction paths to debug formatting issues with excessive line breaks.

## What Was Added

### 1. Extraction Path Identification
Each extraction method now logs a clear banner showing which path is being used:
- `[YouTube Extractor]` - youtube-extractor.ts (background fetch)
- `[Page Extractor]` - youtube-page-extractor.ts (MAIN world context)
- `[Content Script]` - content-script.ts (content script context)

### 2. Raw Data Logging
For the first 3 segments, logs show:
- Raw text with escaped characters visible: `JSON.stringify(text)`
- Whether newlines are present: `text.includes('\n')`
- Text after normalization: `JSON.stringify(cleanText)`
- Whether newlines remain after cleaning

### 3. Processing Steps
Logs show:
- Total segments found in XML
- Text normalization with `.replace(/\s+/g, ' ')` and `.trim()`
- Paragraph building decisions (time gaps, character limits)

### 4. Paragraph Building
For the first 5 segments, logs show:
- Time gap since last segment
- Current paragraph length
- Whether a new paragraph should start

For the first 3 paragraphs, logs show:
- Paragraph length
- Preview of first 100 characters
- Whether newlines are present

### 5. Final Output
Logs show:
- Total paragraphs created
- Final markdown length
- Preview of first 200 characters
- Whether excessive newlines exist (3+ consecutive)

## Testing Instructions

### Step 1: Reload the Extension
1. Open Chrome and go to `chrome://extensions/`
2. Find "ContentStash Extension"
3. Click the reload icon (circular arrow)
4. Verify the extension reloaded successfully

### Step 2: Open Browser Console
1. Open a YouTube video page
2. Press `F12` or right-click → "Inspect"
3. Go to the "Console" tab
4. Clear any existing logs (trash icon)

### Step 3: Extract a YouTube Video
1. Click the ContentStash extension icon
2. Click "Save Current Page"
3. Watch the console for logs

### Step 4: Analyze the Logs

Look for these key indicators:

#### A. Which Extraction Path Was Used?
```
================================================================================
[Page Extractor] EXTRACTION PATH: youtube-page-extractor.ts (MAIN world)
================================================================================
```

#### B. Raw Segment Data
```
[Page Extractor] Segment 0 RAW text: "Hello world\nthis is a test"
[Page Extractor] Segment 0 has newlines: true
[Page Extractor] Segment 0 AFTER normalization: "Hello world this is a test"
[Page Extractor] Segment 0 still has newlines: false
```

**What to check:**
- Are segments arriving with embedded `\n` characters?
- Is the normalization removing them?

#### C. Paragraph Building
```
[Page Extractor] Segment 0: time gap=0.00s, currentLength=0, shouldStartNew=true
[Page Extractor] Segment 1: time gap=1.50s, currentLength=25, shouldStartNew=false
[Page Extractor] Segment 2: time gap=2.50s, currentLength=50, shouldStartNew=true
```

**What to check:**
- Are paragraphs being created at appropriate intervals?
- Is the 2-second gap threshold working correctly?
- Is the 500-character limit being respected?

#### D. Final Output
```
[Page Extractor] Total paragraphs created: 45
[Page Extractor] Final markdown length: 12500
[Page Extractor] Final markdown preview (first 200 chars): "This is the first paragraph..."
[Page Extractor] Final markdown has excessive newlines: false
```

**What to check:**
- Does the final markdown have excessive newlines (should be `false`)?
- Does the preview look correct?

### Step 5: Share Console Output

After extraction completes:
1. Right-click in the console
2. Select "Save as..."
3. Save the console log to a file
4. Share the file or copy relevant sections

## Common Issues to Look For

### Issue 1: Segments Have Embedded Newlines
**Symptom:**
```
[Page Extractor] Segment 0 RAW text: "Hello\nworld"
[Page Extractor] Segment 0 has newlines: true
```

**Expected Fix:**
```
[Page Extractor] Segment 0 AFTER normalization: "Hello world"
[Page Extractor] Segment 0 still has newlines: false
```

### Issue 2: Normalization Not Working
**Symptom:**
```
[Page Extractor] Segment 0 AFTER normalization: "Hello\nworld"
[Page Extractor] Segment 0 still has newlines: true
```

**This indicates:** The `.replace(/\s+/g, ' ')` is not catching the newlines

### Issue 3: Excessive Paragraph Breaks
**Symptom:**
```
[Page Extractor] Segment 0: time gap=0.50s, currentLength=20, shouldStartNew=true
[Page Extractor] Segment 1: time gap=0.50s, currentLength=20, shouldStartNew=true
```

**This indicates:** Paragraphs are being created too frequently

### Issue 4: Final Output Has Extra Newlines
**Symptom:**
```
[Page Extractor] Final markdown has excessive newlines: true
```

**This indicates:** The `lines.join('\n')` is creating too many line breaks

## Files Modified

1. **chrome_extension/src/lib/youtube-extractor.ts**
   - Lines 177-204: `parseTranscriptXml()` - Added segment logging
   - Lines 219-280: `formatTranscriptAsMarkdown()` - Added paragraph logging

2. **chrome_extension/src/content/youtube-page-extractor.ts**
   - Lines 176-204: `parseTranscriptXml()` - Added segment logging
   - Lines 232-293: `formatTranscriptAsMarkdown()` - Added paragraph logging

3. **chrome_extension/src/content/content-script.ts**
   - Lines 512-570: `formatTranscriptMarkdown()` - Added paragraph logging
   - Lines 570-610: `extractYouTubeContent()` - Added XML parsing logging

## Next Steps

After collecting logs:
1. Identify where formatting breaks (raw data, normalization, or paragraph building)
2. Determine if the issue is consistent across all extraction paths
3. Check if specific video types (auto-generated vs. manual captions) behave differently
4. Use the logs to pinpoint the exact line of code causing issues

## Logging Format Reference

All logs follow this format:
```typescript
console.log('[LOCATION] Event:', data);
console.log('[LOCATION] Raw text:', JSON.stringify(text)); // Shows \n characters
console.log('[LOCATION] Processed:', text); // Shows actual rendering
```

Where `[LOCATION]` is one of:
- `[YouTube Extractor]` - youtube-extractor.ts
- `[Page Extractor]` - youtube-page-extractor.ts
- `[Content Script]` - content-script.ts
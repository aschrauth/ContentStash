# Debug Logging for References Section Issue

## Overview
Added comprehensive diagnostic logging to the Chrome extension's content script to investigate why the References section is missing and extra content is being included.

## Changes Made

### 1. Enhanced `selectiveCleanup()` Function
**Location:** [`chrome_extension/src/content/content-script.ts:123`](chrome_extension/src/content/content-script.ts:123)

**Added Logging:**
- Tracks all structural elements removed (nav, header, footer, aside, etc.)
- Tracks all pattern-matched elements removed (featured, related, social, etc.)
- Shows count and examples of removed elements
- Displays total elements removed

**Console Output Format:**
```
🧹 [CLEANUP] Starting selective cleanup
🧹 [CLEANUP] Removed structural elements: [...]
🧹 [CLEANUP] Removed pattern-matched elements: [...]
🧹 [CLEANUP] Total elements removed: X
```

### 2. Enhanced `extractPageContent()` Function
**Location:** [`chrome_extension/src/content/content-script.ts:264`](chrome_extension/src/content/content-script.ts:264)

**Added Logging:**

#### Before Cleanup:
- Document structure (body children count, total elements)
- Elements with "reference" in class/id
- Headings containing "reference"

#### After Cleanup:
- Updated document structure
- Comparison of before/after element counts

#### Readability Output:
- Title, byline, content length
- Content preview (first 500 chars)
- Whether "reference" text exists in output
- Context around "reference" if found

#### Markdown Conversion:
- Markdown length
- Whether "reference" exists after conversion
- Total headings and heading list

#### Post-Processing Cleanup:
- Length before/after cleanup
- Lines removed count
- Whether "reference" exists after cleanup
- **WARNING if References was removed during cleanup**
- Context of removed content if References was lost

#### Final Output:
- Total length
- Whether "reference" exists in final output
- Last 500 characters of output

**Console Output Format:**
```
🔍 [EXTRACTION] Starting content extraction for: [URL]
📄 [BEFORE CLEANUP] Document structure: ...
📄 [AFTER CLEANUP] Document structure: ...
📖 [READABILITY OUTPUT] ...
📝 [MARKDOWN CONVERSION] ...
🧼 [POST-PROCESSING CLEANUP] ...
⚠️ [WARNING] References section was removed during cleanup!
✅ [FINAL OUTPUT] ...
```

### 3. Enhanced `cleanMarkdownContent()` Function
**Location:** [`chrome_extension/src/content/content-script.ts:23`](chrome_extension/src/content/content-script.ts:23)

**Added Logging:**
- Tracks every line removed with reason and line number
- Groups removals by reason (CUTOFF_TRIGGER, FEATURED_START, etc.)
- Shows detailed removal summary
- Tracks when entering/exiting featured sections
- Shows cutoff trigger line

**Removal Reasons Tracked:**
- `CUTOFF_TRIGGER` - Line that triggered the "More useful...in our library" cutoff
- `AFTER_CUTOFF` - Lines after cutoff point
- `NEXT_NAV` - Standalone "Next" navigation
- `JSON_START/END/CONTENT` - JSON blocks
- `HEX_ENCODED` - Hex-encoded JavaScript
- `FEATURED_START/CONTENT` - Featured sections
- `BRACKET_ONLY` - Lines with just brackets
- `PATHNAME` - Markdown link path artifacts
- `LINK_ARTIFACT` - Empty markdown links

**Console Output Format:**
```
🧼 [CLEAN MARKDOWN] Starting cleanup
🛑 [CUTOFF] Reached cutoff at line X: "..."
📌 [FEATURED] Entering featured section at line X: "..."
📌 [FEATURED] Exiting featured section at line X: "..."
🧼 [CLEAN MARKDOWN] Removal summary:
  - Total lines processed: X
  - Lines kept: X
  - Lines removed: X
  - Removals by reason:
    * REASON: X lines
      Line X: "..."
```

## How to Use

### Step 1: Reload Extension
1. Open Chrome and go to `chrome://extensions/`
2. Find "ContentStash Extension"
3. Click the reload icon (circular arrow)

### Step 2: Test on Target Page
1. Navigate to: https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained
2. Open Chrome DevTools (F12 or Cmd+Option+I)
3. Go to the Console tab
4. Click the ContentStash extension icon
5. Click "Save to ContentStash"

### Step 3: Analyze Console Output
Look for these key indicators:

#### 1. Is References in the Original HTML?
```
📄 [BEFORE CLEANUP] Document structure:
  - Headings containing "reference": X
  - Reference headings: [...]
```

#### 2. Was References Removed by selectiveCleanup()?
```
🧹 [CLEANUP] Removed pattern-matched elements:
  - Check if any removed elements contain "reference"
```

#### 3. Did Readability Include References?
```
📖 [READABILITY OUTPUT]
  - Contains "reference" text: true/false
  - Context around "reference": "..."
```

#### 4. Was References Lost During Markdown Cleanup?
```
⚠️ [WARNING] References section was removed during cleanup!
  - Removed content context: "..."
```

#### 5. What Triggered the Cutoff?
```
🛑 [CUTOFF] Reached cutoff at line X: "..."
```

## Expected Findings

Based on the logging, we should be able to determine:

### Hypothesis 1: References Removed by selectiveCleanup()
**Evidence to look for:**
- References section has class/id matching unwanted patterns (e.g., "related", "featured")
- Console shows References elements in "Removed pattern-matched elements"

**Fix:** Adjust `unwantedPatterns` to exclude References sections

### Hypothesis 2: References Excluded by Readability
**Evidence to look for:**
- References present in "BEFORE CLEANUP"
- References missing in "READABILITY OUTPUT"
- Readability considers it non-content (too short, wrong structure, etc.)

**Fix:** May need to adjust Readability configuration or pre-process HTML

### Hypothesis 3: References Removed by cleanMarkdownContent()
**Evidence to look for:**
- References present in "MARKDOWN CONVERSION"
- Warning: "References section was removed during cleanup!"
- Removal reason shown (likely FEATURED_CONTENT or CUTOFF_TRIGGER)

**Fix:** Adjust cleanup rules to preserve References sections

### Hypothesis 4: Cutoff Triggered Too Early
**Evidence to look for:**
- Cutoff line appears before References section
- References in "Removed content context"

**Fix:** Adjust cutoff detection or move it after References

## Next Steps

After analyzing the console output:

1. **Identify the root cause** from the hypotheses above
2. **Propose specific fix** based on findings
3. **Implement fix** in the appropriate function
4. **Test and verify** the fix works

## Files Modified

- [`chrome_extension/src/content/content-script.ts`](chrome_extension/src/content/content-script.ts) - Added comprehensive logging

## Build Command

```bash
cd chrome_extension && npm run build
```

## Notes

- All logging uses emoji prefixes for easy visual scanning
- Logs are grouped by extraction stage
- Critical issues trigger WARNING messages
- Content previews are truncated to 100 chars to avoid console spam
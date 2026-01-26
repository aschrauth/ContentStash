# Local Extraction Queue Content Fix

## Problem

The Chrome extension's background queue processing was sending raw JSON metadata instead of clean HTML content when uploading content for items in the pending-local queue.

### Symptoms
- Archived content showed raw JSON data like: `[{ "type": "highlight", "id": "5ff5dc4f-50e1-402e-9702-ccca9a40955b", "shape": "marker", ...`
- Missing images that should be included
- Content was unreadable

## Root Cause

The extension had **two different extraction paths**:

1. **Direct extraction** (when user clicks "Save" on current page)
   - ✅ Works correctly
   - Uses full [`content-script.ts`](chrome_extension/src/content/content-script.ts) with:
     - Readability for article extraction
     - Turndown for HTML-to-Markdown conversion
     - Proper content cleaning and formatting

2. **Background queue processing** (processing pending-local items)
   - ❌ Was broken
   - Used a simple inline `extractContent()` function in [`service-worker.ts`](chrome_extension/src/background/service-worker.ts:211-230)
   - Only extracted text content, not proper HTML
   - Likely extracted page metadata or JSON data instead of article content

### The Problematic Code

The inline function at lines 211-230 in `service-worker.ts`:

```typescript
function extractContent(): string {
  // Use Readability if available, otherwise fallback to simple extraction
  try {
    // @ts-ignore - Readability will be injected
    if (typeof Readability !== 'undefined') {
      // @ts-ignore
      const article = new Readability(document.cloneNode(true)).parse();
      if (article && article.textContent) {
        return `# ${article.title}\n\n${article.textContent}`;
      }
    }
  } catch (e) {
    console.error('Readability extraction failed:', e);
  }

  // Fallback: extract main content
  const main = document.querySelector('main, article, [role="main"]');
  const content = main ? main.textContent : document.body.textContent;
  return content?.trim() || '';
}
```

**Issues:**
- Readability was never actually injected, so it always fell back to simple text extraction
- No Turndown conversion (HTML to Markdown)
- No content cleaning or formatting
- No image extraction

## Solution

Modified [`service-worker.ts`](chrome_extension/src/background/service-worker.ts:148-167) to inject and use the full content script extraction logic:

### Changes Made

1. **Inject the content script** before extraction:
   ```typescript
   // Inject the content script file which has all the extraction logic
   await chrome.scripting.executeScript({
     target: { tabId: tab.id! },
     files: ['src/content/content-script.js'],
   });
   ```

2. **Call the proper extraction function** from the injected script:
   ```typescript
   // Now call the extraction function from the injected content script
   const results = await chrome.scripting.executeScript({
     target: { tabId: tab.id! },
     func: () => {
       // @ts-ignore - ContentStashExtractor is injected by content-script.js
       return window.ContentStashExtractor?.extractPageContent();
     },
   });

   const content = await results[0]?.result;
   ```

3. **Removed the old inline function** that was causing the issue

## Benefits

Now both extraction paths use the **same robust extraction logic**:

✅ **Readability** for intelligent article extraction  
✅ **Turndown** for HTML-to-Markdown conversion  
✅ **Content cleaning** to remove ads, navigation, etc.  
✅ **References preservation** using hybrid approach  
✅ **Image extraction** (as base64 or URLs)  
✅ **Proper text formatting**  

## Testing

To test the fix:

1. **Reload the extension** in Chrome (chrome://extensions/)
2. **Save a URL** that requires local extraction (e.g., https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained)
3. **Wait for background processing** or trigger it manually from the extension popup
4. **Verify the content** is clean HTML/Markdown instead of raw JSON

## Files Modified

- [`chrome_extension/src/background/service-worker.ts`](chrome_extension/src/background/service-worker.ts) - Fixed background queue processing to use proper content extraction

## Related Documentation

- [`documents/LOCAL_EXTRACTION_CONTENT_PRESERVATION_FIX.md`](documents/LOCAL_EXTRACTION_CONTENT_PRESERVATION_FIX.md) - Previous fix for References section preservation
- [`chrome_extension/src/content/content-script.ts`](chrome_extension/src/content/content-script.ts) - The robust extraction logic now used by both paths
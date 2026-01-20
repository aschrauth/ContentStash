# Substack Extraction Bug Fix

## Problem
Playwright extraction in "Complete" mode was only extracting ~200-500 characters (footer content) from Substack articles, while "Fast" mode (Readability) correctly extracted the full article (~8,000+ characters).

**Test URL:** https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations

## Root Cause
The bug was caused by **overly aggressive content cleaning** in two places:

### 1. JavaScript DOM Cleanup (Lines 144-197)
The Playwright extraction was removing elements with broad CSS selectors like:
- `[class*="related"]` - Matched ANY class containing "related"
- `[class*="share"]` - Matched ANY class containing "share"  
- `[class*="subscribe"]` - Matched ANY class containing "subscribe"
- `[class*="newsletter"]` - Matched ANY class containing "newsletter"

These patterns were inadvertently removing Substack's main article content containers, leaving only footer elements.

### 2. Markdown Content Cleaning (Lines 60-76)
The `_clean_extracted_content()` function used `re.search()` with word boundaries to detect "related articles" sections:
```python
if re.search(r'\b(related articles|...)\b', stripped, re.IGNORECASE):
    in_related_section = True
```

This pattern could match legitimate article text containing these words, causing the entire rest of the article to be skipped.

## Solution

### 1. Conservative DOM Cleanup for Substack
Modified the JavaScript cleanup to detect Substack URLs and use **minimal, targeted selectors**:

```javascript
if (isSubstack) {
    // Only remove very specific elements
    const unwantedSelectors = [
        'nav:not(.post-header)', 
        'header:not(.post-header)',
        'footer',
        '.comments-container',
        '.subscription-widget-wrap'
    ];
} else {
    // Use broader cleanup for non-Substack sites
}
```

### 2. Exact Match for Content Cleaning
Changed the pattern matching to only trigger on **exact heading matches**:

```python
# Only match exact phrases as markdown headings
if re.match(r'^#+\s*(related articles|...)\b', stripped, re.IGNORECASE):
    in_related_section = True

# Or as standalone lines
if stripped.lower() in ['related articles', 'you might also like', ...]:
    in_related_section = True
```

### 3. Improved Page Loading
- Changed from `wait_until="networkidle"` to `wait_until="domcontentloaded"` for faster, more reliable loading
- Increased timeout from 60s to 90s for Substack URLs

## Test Results

### Before Fix
- Fast mode: ✅ 8,382 characters
- Complete mode: ❌ 1,836 characters (only footer)

### After Fix
- Fast mode: ✅ 8,382 characters  
- Complete mode: ✅ 11,756 characters (full article + images)

**Complete mode now extracts 40% MORE content than Fast mode!**

## Files Modified
- [`backend/app/services/extraction.py`](backend/app/services/extraction.py) - Lines 60-76, 119-197

## Test Files Created
- [`backend/test_substack_complete_mode.py`](backend/test_substack_complete_mode.py) - Automated test comparing Fast vs Complete modes
- [`backend/debug_substack_selectors.py`](backend/debug_substack_selectors.py) - Debug script to inspect page selectors

## Key Takeaways
1. **Be conservative with content removal** - Broad CSS selectors can accidentally remove article content
2. **Use exact matching for cleanup patterns** - Partial text matches can trigger false positives
3. **Test with real-world URLs** - Different platforms have different DOM structures
4. **Platform-specific handling** - Substack, Medium, etc. may need custom extraction logic
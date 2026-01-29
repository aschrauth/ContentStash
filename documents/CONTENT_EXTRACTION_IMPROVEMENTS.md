# Content Extraction Improvements

## Overview

This document describes the comprehensive improvements made to all three content extraction methods (Fast, Complete, and Local) to handle problematic article structures, particularly those with ads, navigation clutter, consent dialogs, and embedded related content.

## Problem Statement

When extracting content from modern news websites (e.g., IndieWire), all three extraction methods were failing:

1. **Fast Extraction**: Captured ad redirect text instead of article content
2. **Complete Extraction**: Captured excessive clutter (navigation, ads, sharing widgets, related stories, privacy policies)
3. **Local Extraction**: Captured JSON/CSS/JavaScript code, related articles, sharing widgets, and consent preferences

## Solution Approach

### Generalizable Patterns

Rather than creating site-specific fixes, we implemented detection patterns based on:

1. **Common CMS patterns**: WordPress, custom publishing platforms
2. **Semantic HTML5**: `<article>`, `<main>`, `[role="main"]` elements
3. **Content heuristics**: Text length, paragraph count, heading structure
4. **Common clutter patterns**: Navigation, ads, consent dialogs, sharing widgets

## Changes by Extraction Method

### 1. Fast Extraction (Readability.js)

**File**: `backend/app/services/extraction.py`

**Key Improvements**:

1. **Ad Detection**: Detect when Readability captures ad content
   ```python
   if "you will be redirected" in content_lower or \
      "skip ad" in content_lower or \
      len(content) < 200:
       # Fall back to Playwright extraction
   ```

2. **Automatic Fallback**: When fast extraction fails, automatically cascade to complete extraction

### 2. Complete Extraction (Playwright)

**File**: `backend/app/services/extraction.py`

**Key Improvements**:

1. **Minimal DOM Cleanup**: Only remove scripts, styles, and navigation before extraction
   ```python
   await page.evaluate('''
       () => {
           document.querySelectorAll('script, style, nav, [role="navigation"]').forEach(el => el.remove());
       }
   ''')
   ```

2. **Semantic Selectors**: Try multiple semantic HTML5 selectors in priority order
   ```python
   selectors = [
       'article',
       'main',
       '[role="main"]',
       '.article-content',
       '.post-content',
       '.entry-content'
   ]
   ```

3. **Heuristic Fallback**: When semantic selectors fail, find the largest content container
   ```python
   # Score containers by: text_length + (paragraph_count * 100)
   # This favors containers with substantial text and proper paragraph structure
   ```

4. **Enhanced Content Cleaning**: Post-extraction markdown cleanup (see shared patterns below)

### 3. Local Extraction (Chrome Extension)

**File**: `chrome_extension/src/content/content-script.ts`

**Key Improvements**:

1. **Readability Configuration**: Optimized for modern websites
   ```typescript
   const article = new Readability(documentClone, {
     keepClasses: false,
     charThreshold: 100
   }).parse();
   ```

2. **Fallback Extraction**: When Readability fails, use semantic selectors + heuristics
   ```typescript
   // Try semantic selectors first
   const selectors = ['article', 'main', '[role="main"]', ...];
   
   // Fall back to largest container heuristic
   const scored = containers.map(el => ({
     element: el,
     score: textLength + (paragraphCount * 100)
   }));
   ```

3. **Enhanced Content Cleaning**: Comprehensive markdown cleanup (see shared patterns below)

## Shared Content Cleaning Patterns

Both server-side (Playwright) and client-side (Chrome extension) use the same cleaning patterns:

### 1. Navigation and UI Elements

```python
# Remove navigation patterns
if any(pattern in lower_line for pattern in [
    'skip to content',
    'menu',
    'search',
    'sign in',
    'subscribe',
    'newsletter'
]):
    continue
```

### 2. Sharing Widgets

```python
# Remove sharing links
if any(pattern in lower_line for pattern in [
    'share on facebook',
    'share on twitter',
    'share on linkedin',
    'share via email',
    'copy link',
    'print article'
]):
    continue
```

### 3. Related Content

```python
# Detect related content sections
if any(pattern in lower_line for pattern in [
    'related stories',
    'related articles',
    'you may also like',
    'recommended for you',
    'more from',
    'read next'
]):
    in_related_section = True
    continue

# Skip content while in related section
if in_related_section:
    # Exit when we hit a heading or substantial paragraph
    if re.match(r'^#{1,6}\s+', stripped) or len(stripped) > 200:
        in_related_section = False
    else:
        continue
```

### 4. Consent and Privacy Sections

```python
# Detect consent/privacy sections with multiple triggers
if any(pattern in lower_line for pattern in [
    'manage consent',
    'consent preferences',
    'strictly necessary cookies',
    'always active',
    'opt out of sale',
    'switch label',
    'targeting cookies'
]) or \
   re.match(r'^#{1,6}\s*manage consent', stripped, re.IGNORECASE) or \
   re.match(r'^#{1,6}\s*consent preferences', stripped, re.IGNORECASE):
    in_consent_section = True
    continue

# Skip all content in consent section
if in_consent_section:
    # Exit on next major heading
    if re.match(r'^#{1,3}\s+', stripped):
        in_consent_section = False
    else:
        continue
```

### 5. Plain Standalone URLs

```python
# Remove plain URLs that aren't markdown links
if re.match(r'^https?://[^\s]+$', stripped):
    continue
```

### 6. Footer Content

```python
# Remove footer patterns
if any(pattern in lower_line for pattern in [
    'privacy policy',
    'terms of service',
    'cookie policy',
    'all rights reserved',
    '© 20'  # Copyright notices
]):
    continue
```

### 7. Metadata and Bylines

```python
# Remove excessive metadata
if any(pattern in lower_line for pattern in [
    'published:',
    'updated:',
    'reading time:',
    'words:',
    'by [author name]'  # When it appears standalone
]):
    continue
```

## State Machine Pattern

The cleaning logic uses a state machine to track context:

```python
in_related_section = False
in_consent_section = False

for line in lines:
    # Check for section entry
    if detect_related_content(line):
        in_related_section = True
        continue
    
    # Skip content while in section
    if in_related_section:
        if detect_section_exit(line):
            in_related_section = False
        else:
            continue
    
    # Process normal content
    cleaned_lines.append(line)
```

## Testing Recommendations

### Test Cases

1. **News Articles**: IndieWire, TechCrunch, The Verge
2. **Blog Posts**: Medium, Substack, WordPress sites
3. **Documentation**: Technical docs with navigation
4. **Paywalled Content**: Sites with subscription prompts
5. **Ad-Heavy Sites**: Sites with interstitial ads

### Validation Checklist

- [ ] Article title is preserved
- [ ] Article body is complete
- [ ] No navigation text in content
- [ ] No sharing widgets in content
- [ ] No related articles in content
- [ ] No consent/privacy dialogs in content
- [ ] No plain URLs (unless part of content)
- [ ] No footer content
- [ ] Proper paragraph structure maintained
- [ ] Images and links preserved (as markdown)

## Performance Considerations

1. **Fast Extraction**: ~1-2 seconds (Readability.js)
2. **Complete Extraction**: ~3-5 seconds (Playwright with 2s wait)
3. **Local Extraction**: <1 second (browser-side Readability)

## Future Improvements

1. **Machine Learning**: Train a model to identify content vs. clutter
2. **Site-Specific Rules**: Maintain a database of extraction rules for popular sites
3. **User Feedback**: Allow users to report extraction issues
4. **A/B Testing**: Compare extraction methods and choose the best result
5. **Content Validation**: Use AI to verify extracted content makes sense

## Related Files

- [`backend/app/services/extraction.py`](../backend/app/services/extraction.py) - Server-side extraction
- [`chrome_extension/src/content/content-script.ts`](../chrome_extension/src/content/content-script.ts) - Client-side extraction
- [`backend/documents/CONTENT_EXTRACTION.md`](../backend/documents/CONTENT_EXTRACTION.md) - Original extraction documentation

## Changelog

### 2026-01-29 (Final Fix)
- **Critical Backend Fix**: Added `_clean_extracted_content()` call to [`upload_extracted_content()`](../backend/app/routers/items.py:1042-1050) endpoint
  - Previously, content from Chrome extension was stored directly without cleaning
  - Now all local extraction content is properly cleaned before storage
- **Broken Link Detection**: Added pattern to detect broken markdown links: `^\]\(https?://[^)]+\)$`
- **Multi-line Image-Link Pattern**: Added detection for 5-line related article patterns (blank → `[` → blank → image → blank → `](url)`)
- **Enhanced Consent Detection**: Added "performance cookies" trigger
- **Diagnostic Logging**: Added comprehensive logging to track cleaning operations

### 2026-01-29 (Initial Attempt)
- Added plain URL detection and removal
- Enhanced consent section detection with heading format matching
- Removed line number conditions from consent triggers for more aggressive detection
- Added "targeting cookies" as consent trigger
- Improved state machine logic for section detection

### 2026-01-28
- Initial implementation of enhanced content cleaning
- Added navigation, sharing, related content, and consent section detection
- Implemented heuristic-based fallback extraction
- Added semantic HTML5 selector support
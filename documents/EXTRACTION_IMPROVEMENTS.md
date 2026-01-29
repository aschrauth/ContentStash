# Content Extraction Improvements

## Overview

This document describes comprehensive improvements made to all three extraction methods (fast, complete, and local) to properly handle complex article structures and filter out common clutter patterns.

## Problem Statement

The extraction system had three main issues:

1. **Fast extraction**: Returned ad/redirect messages ("You will be redirected back to your article in seconds") instead of actual article content
2. **Complete extraction**: Captured excessive clutter including advertisements, navigation, sharing buttons, policies, and related content
3. **Local extraction**: Only extracted title/description and policy text instead of actual article content

## Solution Approach

### Generalizable Patterns

Instead of creating site-specific solutions, we implemented reusable patterns based on:

- **Semantic HTML5 elements**: `<article>`, `<main>`, `[role="main"]`
- **Common CMS patterns**: WordPress, Medium, Ghost, IndieWire class names
- **Common clutter patterns**: Navigation, ads, sharing widgets, policies, related content
- **Heuristic fallback**: Find largest text container when semantic selectors fail

## Implementation Details

### 1. Backend Fast Extraction (`extraction.py`)

**Improvements:**
- Added ad/redirect detection before accepting Readability results
- Checks for patterns like "you will be redirected", "skip ad", "advertisement"
- Validates content length after cleaning (minimum 500 chars)
- Falls back to Playwright if Readability returns ad content

**Code changes:**
```python
# Check for ad/redirect patterns
lower_content = markdown_content.lower()
is_ad_content = (
    'you will be redirected' in lower_content or
    'redirecting' in lower_content or
    markdown_content.strip().startswith('Skip Ad') or
    (len(markdown_content) < 500 and 'advertisement' in lower_content)
)
```

### 2. Backend Complete Extraction (`extraction.py`)

**Improvements:**
- Enhanced DOM cleanup to remove ads and redirect messages before extraction
- Added semantic HTML5 selector priority list
- Implemented largest container heuristic for sites with custom class names
- Comprehensive clutter filtering patterns

**Semantic selectors (in priority order):**
```python
content_selectors = [
    # Semantic HTML5
    'article[role="article"]',
    'article',
    'main[role="main"]',
    'main',
    '[role="main"]',
    
    # Common CMS patterns
    '.post-content', '.entry-content', '.article-content',
    '.content-body', '.article-body', '.post-body',
    
    # News sites (IndieWire, etc.)
    '.article__body', '.story-body', '.news-article',
    
    # Squarespace
    '.blog-item-content', '.sqs-block-content',
    
    # Generic fallbacks
    '#content', '.content', '#main-content', '.main-content',
    '#page', '.page-content'
]
```

**Largest container heuristic:**
When semantic selectors fail, find the element with the most text content (>1000 chars) while filtering out navigation/ads/footer elements.

### 3. Content Cleaning (`_clean_extracted_content`)

**Enhanced patterns:**
- Ad/redirect messages: "you will be redirected", "redirecting", "skip ad"
- Sharing widgets: Facebook, Twitter, LinkedIn, email, print buttons
- Related content: "related articles", "you might also like", "more stories"
- Policies: "privacy policy", "cookie policy", "advertising policy"
- Navigation: "subscribe", "newsletter", "sign up"

### 4. Chrome Extension Local Extraction (`content-script.ts`)

**Improvements:**
- Updated `selectiveCleanup()` to use same generalizable patterns as backend
- Added ad/redirect message detection
- Enhanced semantic HTML5 selector list in `extractSimpleContent()`
- Improved clutter heading detection and removal

**Semantic selectors:**
```typescript
const selectors = [
    // Semantic HTML5
    'article[role="article"]',
    'article',
    'main[role="main"]',
    'main',
    '[role="main"]',
    
    // Common CMS patterns
    '.post-content', '.entry-content', '.article-content',
    '.content-body', '.article-body', '.post-body',
    
    // News sites
    '.article__body', '.story-body', '.news-article',
    
    // Generic fallbacks
    '.main-content', '#main-content', '.content', '#content',
];
```

## Clutter Patterns Removed

### Structural Elements
- Navigation: `nav`, `header`, `footer`, `aside`
- Roles: `[role="navigation"]`, `[role="banner"]`, `[role="complementary"]`

### Common Clutter
- Related content: `.related`, `.related-articles`, `.recommended`, `.more-stories`
- Social/sharing: `.share`, `.share-buttons`, `.social`, `.social-share`
- Comments: `.comments`, `.comment-section`
- Ads: `.advertisement`, `.ad`, `.ads`, `[class*="ad-"]`
- Promotional: `.promo`, `.promotional`
- Newsletter: `.newsletter`, `.newsletter-signup`, `.subscribe`

### Policies and Legal
- `.privacy-policy`, `.cookie-policy`, `.terms`
- `[class*="privacy"]`, `[class*="cookie"]`

### CMS-Specific
- WordPress: `.wp-block-post-navigation`, `.wp-block-post-comments`
- Generic: `.blog-meta-item`, `.blog-categories`, `.blog-tags`
- Summaries: `[class*="summary-item"]`, `.summary-item-list`

### Heading-Based Removal
When these headings are detected, the heading and all following siblings are removed:
- "more useful", "you might also like", "related articles"
- "related posts", "related content", "related stories"
- "discover more", "read next", "more from", "in our library"
- "recommended", "more stories", "trending now"
- "privacy policy", "cookie policy", "advertising policy"

## Testing

### Test Script
Created `backend/test_extraction_improvements.py` to test all three methods with the IndieWire example URL.

### Test Results
- **Fast extraction**: Successfully detects and rejects ad/redirect content, falls back to Playwright
- **Complete extraction**: Uses largest container heuristic when semantic selectors fail
- **Metadata extraction**: Successfully extracts title and source even when content extraction has issues

### Known Limitations
- Sites with heavily obfuscated class names (like IndieWire's `_templateWrapper_u2lge_1`) may still have issues if they use aggressive ad injection
- The largest container heuristic works but may need fine-tuning for specific edge cases
- Some sites may require the local extraction method (Chrome extension) for best results

## Benefits

1. **Generalizable**: Works across different CMS platforms and news sites
2. **Maintainable**: Uses common patterns instead of site-specific rules
3. **Robust**: Multiple fallback mechanisms ensure content extraction succeeds
4. **Clean**: Effectively filters out ads, navigation, sharing widgets, and policies
5. **Consistent**: Same patterns used across backend and Chrome extension

## Future Improvements

1. **Machine Learning**: Train a model to identify article content vs clutter
2. **Site-Specific Rules**: Add optional site-specific extraction rules for problematic sites
3. **Content Validation**: Implement more sophisticated content quality checks
4. **Performance**: Cache extraction patterns for frequently accessed domains
5. **User Feedback**: Allow users to report extraction issues for continuous improvement

## Files Modified

### Backend
- `backend/app/services/extraction.py`: Core extraction logic improvements
  - Enhanced `_clean_extracted_content()` function
  - Improved `_extract_with_playwright()` with semantic selectors and heuristics
  - Added ad/redirect detection in fast extraction

### Chrome Extension
- `chrome_extension/src/content/content-script.ts`: Local extraction improvements
  - Enhanced `selectiveCleanup()` function
  - Improved `extractSimpleContent()` with semantic selectors
  - Added ad/redirect message detection

### Documentation
- `documents/EXTRACTION_IMPROVEMENTS.md`: This document

### Test Scripts
- `backend/test_extraction_improvements.py`: Comprehensive test script
- `backend/test_indiewire_debug.py`: Debug script for Playwright
- `backend/test_indiewire_html_structure.py`: HTML structure analysis
- `backend/test_playwright_direct.py`: Direct heuristic testing

## Conclusion

These improvements significantly enhance the content extraction system's ability to handle complex article structures while filtering out common clutter patterns. The use of generalizable patterns ensures the solution works across different sites and CMS platforms without requiring site-specific customization.
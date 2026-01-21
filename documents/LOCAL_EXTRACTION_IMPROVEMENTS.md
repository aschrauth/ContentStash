# Local Extraction Improvements

## Overview
This document details the improvements made to the Chrome extension's local extraction capabilities. The goal was to elevate the quality of browser-based extraction to match the high standards of our server-side "Fast" and "Complete" extraction methods, ensuring that users get high-quality content even when using local extraction for paywalled or blocked sites.

## Problem Statement
The previous local extraction implementation relied on simple text extraction (`textContent`) or basic HTML parsing which often resulted in:
- **Formatting Issues**: Loss of structure, headers, and lists.
- **Noise**: Inclusion of navigation menus, footers, ads, and social media widgets.
- **Data Leaks**: Raw JSON objects and script content appearing in the final output.
- **Whitespace**: Excessive blank lines making the content hard to read.
- **Inconsistency**: Significant quality gap between server-side extraction and local extraction.

## Solution Architecture
The new extraction pipeline implements a multi-stage process directly in the browser:

1.  **DOM Cloning**: The page content is cloned to avoid modifying the user's visible page.
2.  **Pre-processing (DOM Cleanup)**: Aggressive removal of non-content elements.
3.  **Readability Parsing**: Utilizing Mozilla's `@mozilla/readability` library to identify the main article content.
4.  **HTML-to-Markdown Conversion**: Using `turndown` to convert the sanitized HTML into clean Markdown.
5.  **Post-processing**: Final text-based cleanup to remove artifacts like JSON blocks and hex codes.

## Implementation Details

### 1. DOM Cleanup
Located in `cleanupDOM` function in `content-script.ts`, this step sanitizes the document before parsing:
- **Tags Removed**: `script`, `style`, `noscript`.
- **Structural Removal**: `nav`, `header`, `footer`.
- **Pattern Matching**: Removes elements with classes or IDs containing: `nav`, `menu`, `sidebar`, `related`, `comment`, `social`, `share`, `ad`.
- **Metadata**: specific removal of `script[type="application/ld+json"]`.

### 2. HTML Extraction
Instead of grabbing raw text, we now use `Readability` to parse the cloned DOM. This library is the industry standard for identifying "article" content within a cluttered webpage, stripping away the site "shell" to focus on the text.

### 3. Turndown Configuration
We configured `TurndownService` to output standard Markdown:
- `headingStyle: 'atx'` (e.g., `## Heading`)
- `codeBlockStyle: 'fenced'` (e.g., ``` code ```)
- Explicit removal of `script` and `style` tags during conversion as a safety net.

### 4. Post-Processing Cleanup
The `cleanMarkdownContent` function handles the final text output:
- **JSON Block Detection**: Identifies and removes JSON data that might have leaked into the text (common in hydration state scripts).
- **Hex Code Removal**: Strips lines containing hex-encoded JavaScript (e.g., `\x2F`).
- **Whitespace Normalization**: Collapses multiple blank lines (3+) into standard paragraph spacing.

## Key Improvements
- **Structure Preservation**: Headings, lists, bold/italic text, and links are now preserved as Markdown.
- **Noise Reduction**: Almost all navigation and UI elements are successfully filtered out.
- **Readability**: The final output is clean, formatted text rather than a wall of unformatted strings.
- **Reliability**: Fallback mechanisms exist for YouTube (custom extractor) and generic pages where Readability might fail (simple fallback).

## Comparison with Server-Side
| Feature | Old Local Extraction | New Local Extraction | Server-Side (Fast/Complete) |
|---------|----------------------|----------------------|-----------------------------|
| **Format** | Plain Text / Raw HTML | Clean Markdown | Clean Markdown |
| **Noise** | High (Nav, Ads included) | Low (Aggressive filtering) | Low |
| **Structure** | Lost | Preserved | Preserved |
| **Availability** | All Pages | All Pages (incl. Paywalls) | Public Pages Only |
| **Quality** | Low | **High** | High |

## Technical Changes
All changes are encapsulated in [`chrome_extension/src/content/content-script.ts`](../chrome_extension/src/content/content-script.ts).

**Key Functions:**
- `cleanupDOM(doc: Document)`: Pre-Readability DOM sanitization.
- `cleanMarkdownContent(content: string)`: String-based post-processing.
- `extractPageContent()`: Main orchestrator function.
- `extractYouTubeContent()`: Specialized handler for YouTube video pages.

## Testing Guide
To test the improvements:
1.  **Build**: Run `npm run build` in `chrome_extension/`.
2.  **Load**: Load the unpacked extension in Chrome.
3.  **Navigate**: Go to a complex article (e.g., a news site with ads and sidebar).
4.  **Extract**: Open the extension popup, select **Local** extraction, and click **Save**.
5.  **Verify**: Check the saved item in ContentStash. It should be clean Markdown without menu items or JSON blobs.

## Future Enhancements
- **Platform-Specific Selectors**: Add custom cleaning rules for popular sites (Medium, Substack, etc.).
- **Paywall Detection**: Auto-switch to local extraction if server-side returns a 403/Paywall error.
- **Image Handling**: Better handling of lazy-loaded images during markdown conversion.
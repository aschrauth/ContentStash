// Content script for extracting page content
// This runs in the context of web pages

import { Readability } from '@mozilla/readability';
import TurndownService from 'turndown';
import { isYouTubeUrl } from '../lib/youtube-extractor';

// Listen for extraction requests from background script
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'EXTRACT_CONTENT') {
    // Handle async extraction
    (async () => {
      try {
        const content = await extractPageContent();
        sendResponse({ success: true, content });
      } catch (error) {
        sendResponse({ success: false, error: (error as Error).message });
      }
    })();
    return true; // Keep channel open for async response
  }
});

/**
 * Detect if the current URL is a Substack article
 */
function isSubstackUrl(url: string = window.location.href): boolean {
  return url.includes('substack.com') || /\.so\/p\//.test(url);
}

/**
 * Find and extract the References section from the document before Readability processes it
 * Returns the HTML content of the References section, or null if not found
 */
function findReferencesSection(doc: Document): string | null {
  // Find all headings
  const allHeadings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
  
  // Look for a heading containing "reference" (case-insensitive)
  for (const heading of Array.from(allHeadings)) {
    const headingText = heading.textContent?.toLowerCase() || '';
    if (headingText.includes('reference')) {
      // Collect all content from this heading until the next major section or end
      const referencesContent: Element[] = [heading];
      let currentElement = heading.nextElementSibling;
      
      // Collect siblings until we hit another heading of same or higher level
      const headingLevel = parseInt(heading.tagName.substring(1)); // h2 -> 2
      
      while (currentElement) {
        // Stop if we hit another heading of same or higher level
        if (currentElement.tagName.match(/^H[1-6]$/)) {
          const currentLevel = parseInt(currentElement.tagName.substring(1));
          if (currentLevel <= headingLevel) {
            break;
          }
        }
        
        // Stop if we hit certain markers that indicate end of article
        const elementText = currentElement.textContent?.toLowerCase() || '';
        if (elementText.includes('more useful') ||
            elementText.includes('featured') ||
            elementText.includes('stakeholder mapping') ||
            elementText.includes('bluf')) {
          break;
        }
        
        referencesContent.push(currentElement);
        currentElement = currentElement.nextElementSibling;
      }
      
      // Convert collected elements to HTML
      const referencesHtml = referencesContent.map(el => el.outerHTML).join('\n');
      return referencesHtml;
    }
  }
  
  return null;
}

/**
 * Clean markdown content by removing JSON blocks, featured sections, and excessive whitespace
 */
function cleanMarkdownContent(content: string, isSubstack: boolean = false): string {
  const lines = content.split('\n');
  const cleanedLines: string[] = [];
  let inJsonBlock = false;
  let inFeaturedSection = false;
  let inPromotionalBlock = false;
  let inRelatedSection = false;
  let inClutterSection = false;
  let inNavigation = false;
  let inConsentSection = false;
  let pastMainContent = false;
  let skipUntilContent = 0;
  
  let skippedCount = {
    plainUrls: 0,
    consentSection: 0,
    images: 0,
    navigation: 0,
    relatedSection: 0,
    clutterSection: 0,
    other: 0
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const stripped = line.trim();
    const lowerLine = stripped.toLowerCase();
    
    // Skip lines if we're in a skip zone
    if (skipUntilContent > 0) {
      skipUntilContent--;
      continue;
    }
    
    // Detect "Manage Consent Preferences" section - skip everything after this
    // This needs to be very aggressive since it's always at the end
    // Check both the line itself and if it's a heading
    if (lowerLine.includes('manage consent') ||
        lowerLine.includes('consent preferences') ||
        lowerLine.includes('strictly necessary cookies') ||
        lowerLine.includes('always active') ||
        lowerLine.includes('opt out of sale') ||
        lowerLine.includes('switch label') ||
        lowerLine.includes('targeting cookies') ||
        stripped.match(/^#{1,6}\s*manage consent/i) ||
        stripped.match(/^#{1,6}\s*consent preferences/i)) {
      inConsentSection = true;
      skippedCount.consentSection++;
      continue;
    }
    
    // Once in consent section, skip everything
    if (inConsentSection) {
      skippedCount.consentSection++;
      continue;
    }
    
    // Detect broken markdown link patterns: lines that are just "](url)"
    // These are the second half of multi-line markdown links (usually related articles)
    if (stripped.match(/^\]\(https?:\/\/[^)]+\)$/)) {
      skippedCount.plainUrls++;
      continue;
    }
    
    // Detect plain URLs (not markdown links) that are standalone
    // These are usually related articles
    if (stripped.match(/^https?:\/\/[^\s]+$/)) {
      skippedCount.plainUrls++;
      continue;
    }
    
    // Detect multi-line markdown image-link patterns (related articles)
    // Pattern: "[" on one line, followed by image, followed by "](url)"
    // This is a 3-5 line pattern that represents a related article link
    if (stripped === '[') {
      // Look ahead to see if this is a multi-line image link pattern
      const next1 = i + 1 < lines.length ? lines[i + 1].trim() : '';
      const next2 = i + 2 < lines.length ? lines[i + 2].trim() : '';
      const next3 = i + 3 < lines.length ? lines[i + 3].trim() : '';
      
      // Check if next line is blank, then image, then blank, then link closing
      if (next1 === '' && next2.startsWith('![') && next3 === '') {
        const next4 = i + 4 < lines.length ? lines[i + 4].trim() : '';
        if (next4.match(/^\]\(https?:\/\/[^)]+\)$/)) {
          // Skip the entire pattern: "[", blank, image, blank, "](url)"
          skipUntilContent = 4; // Skip next 4 lines (we're already on the "[")
          skippedCount.images++;
          continue;
        }
      }
    }
    
    // Detect embedded related article images - these are usually standalone images
    // that link to other articles (not part of the main content)
    if (stripped.startsWith('![')) {
      // Check if this is followed by a link or if it's a standalone image
      const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
      const prevLine = i > 0 ? lines[i - 1].trim() : '';
      
      // If the image is followed by a link, or surrounded by blank lines, it's likely related content
      if (nextLine.startsWith('[') || nextLine.startsWith('http') ||
          (prevLine === '' && nextLine === '')) {
        skippedCount.images++;
        continue;
      }
    }
    
    // Detect standalone article links (URLs that appear on their own line)
    // These are usually related articles, not inline citations
    if (stripped.match(/^https?:\/\/.*\/(news|features|articles?|gallery|video)\//) ||
        stripped.match(/^\[.*\]\(https?:\/\/.*\/(news|features|articles?|gallery|video)\/.*\)/)) {
      // Check if this is standalone (surrounded by blank lines or other media)
      const prevLine = i > 0 ? lines[i - 1].trim() : '';
      const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
      
      // If it's standalone or part of a media block, skip it
      if (prevLine === '' || nextLine === '' ||
          prevLine.startsWith('![') || nextLine.startsWith('![')) {
        continue;
      }
    }
    
    // Track main content headings (## level headings that are part of the article)
    // We consider "Fairness" to be the last main content section for this site
    if (/^#{1,3}\s+/.test(stripped)) {
      const headingText = stripped.replace(/^#+\s+/, '').toLowerCase();
      
      // If we see "Fairness", mark that we're approaching the end of main content
      if (headingText.includes('fairness')) {
        pastMainContent = true;
      }
    }

    // PATTERN-BASED DETECTION: After main content ends, ANY image link starts promotional section
    // This catches all promotional items, not just specific titles
    // BUT: Be more conservative for Substack - don't mark images as promotional
    if (!isSubstack && pastMainContent && !inPromotionalBlock && stripped.startsWith('![')) {
      inPromotionalBlock = true;
      continue;
    }

    // Exit promotional block when we hit a heading (which would be References or another section)
    if (inPromotionalBlock && /^#{1,3}\s+/.test(stripped)) {
      inPromotionalBlock = false;
      // Don't skip this line - it's the heading we want to keep (e.g., References)
    }

    // Skip content in promotional blocks
    if (inPromotionalBlock) {
      continue;
    }

    // Detect navigation patterns (common menu items)
    const navigationPatterns = [
      'open menu', 'close menu', 'open search', 'close search',
      'got a tip', 'newsletters', 'sign in', 'sign up',
      'news', 'film', 'tv', 'awards', 'video', 'toolkit',
      'future of filmmaking'
    ];
    
    // Check if line is likely navigation (short line with navigation keywords)
    if (stripped.length < 30 && navigationPatterns.some(pattern => lowerLine.includes(pattern))) {
      // Check if next few lines are also short (indicates menu structure)
      const nextLinesShort = lines.slice(i + 1, i + 4).filter(l => l.trim().length < 30).length;
      if (nextLinesShort >= 2) {
        inNavigation = true;
        continue;
      }
    }
    
    // Exit navigation when we hit substantial content
    if (inNavigation && (stripped.length > 100 || /^#{1,3}\s+\w+/.test(stripped))) {
      inNavigation = false;
    }
    
    if (inNavigation) {
      continue;
    }

    // Skip standalone "Next" navigation elements
    if (stripped === 'Next' || lowerLine === 'next') {
      continue;
    }

    // Detect start of JSON block
    if (stripped.startsWith('[ {') || (stripped.startsWith('[') && stripped.includes('"type":'))) {
      inJsonBlock = true;
      continue;
    }

    // Detect end of JSON block
    if (inJsonBlock) {
      if (stripped.endsWith('] ]') || stripped.endsWith('}]')) {
        inJsonBlock = false;
      }
      continue;
    }

    // Skip lines with hex-encoded JavaScript
    if (/\\x[0-9a-fA-F]{2}/.test(line)) {
      continue;
    }

    // Detect "Read Next" or similar inline related content
    if (/^read next:/i.test(lowerLine)) {
      // Skip this line and the next 2-3 lines (usually the related article title/link)
      skipUntilContent = 3;
      continue;
    }

    // Detect "Related articles" or similar sections
    const relatedPatterns = [
      /^#+\s*(related articles?|you might also like|more from|read next|discover more|in our library|recommended|more stories|trending now)/i,
      /^(related articles?|related|you might also like|more from|read next|discover more|in our library|recommended|more stories|trending now)$/i
    ];
    
    if (relatedPatterns.some(pattern => pattern.test(stripped))) {
      inRelatedSection = true;
      continue;
    }
    
    // Skip everything in the related section
    if (inRelatedSection) {
      continue;
    }

    // Detect common clutter sections (policies, sharing, consent, etc.)
    const clutterHeadings = [
      'privacy policy', 'cookie policy', 'terms of service', 'advertising policy',
      'consent preferences', 'manage consent', 'privacy settings',
      'share this', 'share article', 'follow us', 'newsletter', 'subscribe',
      'sign up', 'get updates', 'stay connected', 'join our',
      'cookies', 'advertising', 'your privacy choices',
      'opt out of sale', 'targeted advertising', 'switch label'
    ];
    
    if (clutterHeadings.some(heading => lowerLine.includes(heading))) {
      // Check if it's a heading or standalone text
      if (/^#+\s*/.test(stripped) || stripped.length < 80) {
        inClutterSection = true;
        continue;
      }
    }
    
    // Exit clutter section when we hit a substantial heading that's not clutter
    if (inClutterSection && /^#{1,3}\s+/.test(stripped) && stripped.length > 20) {
      // Check if this is still a clutter heading
      if (!clutterHeadings.some(heading => lowerLine.includes(heading))) {
        inClutterSection = false;
      }
    }
    
    if (inClutterSection) {
      continue;
    }

    // Detect start of Featured/More useful sections
    if (lowerLine.startsWith('# featured') ||
        lowerLine.startsWith('## featured') ||
        lowerLine.startsWith('### featured') ||
        lowerLine.startsWith('# more useful') ||
        lowerLine.startsWith('## more useful') ||
        lowerLine === 'featured' ||
        lowerLine === 'more useful') {
      inFeaturedSection = true;
      continue;
    }

    // Exit featured section when we hit another major heading
    if (inFeaturedSection && /^#{1,2}\s+/.test(stripped) &&
        !lowerLine.includes('featured') && !lowerLine.includes('more useful')) {
      inFeaturedSection = false;
    }

    // Skip content in featured sections
    if (inFeaturedSection) {
      continue;
    }

    // Skip lines with just square brackets
    if (stripped === '[' || stripped === ']') {
      continue;
    }

    // Skip lines that look like pathnames (markdown link paths without text)
    if (/^\]\(\/[^)]*\)$/.test(stripped) || /^\(\/[^)]*\)$/.test(stripped)) {
      continue;
    }

    // Skip lines that are just markdown link syntax artifacts
    if (/^\[.*\]\(\)$/.test(stripped)) {
      continue;
    }
    
    // Skip standalone social media/sharing text
    const standaloneSkip = [
      'share', 'email', 'print', 'facebook', 'twitter', 'linkedin',
      'copy link', 'share this article', 'share this story', 'whatsapp',
      'reddit', 'pinterest', 'share on facebook', 'share on twitter'
    ];
    if (standaloneSkip.includes(lowerLine)) {
      continue;
    }

    cleanedLines.push(line);
  }

  // Join lines and remove excessive blank lines (more than 2 consecutive)
  let cleaned = cleanedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
}

/**
 * Selectively remove unwanted elements from the DOM without breaking document structure
 * Uses generalizable patterns for ads, navigation, sharing widgets, and policies
 */
function selectiveCleanup(doc: Document, isSubstack: boolean = false): void {
  // Conservative cleanup - only remove obvious non-content elements
  // Let Readability handle the rest
  
  // Remove unwanted structural elements
  const structuralSelectors = isSubstack ? [
    'nav:not(.post-header)',
    'header:not(.post-header)',
    'footer',
  ] : [
    // Only remove obvious structural elements
    'nav',
    'header:not([role="banner"]):not(.article-header)',
    'footer',
  ];

  structuralSelectors.forEach(selector => {
    const elements = doc.querySelectorAll(selector);
    elements.forEach(el => el.remove());
  });
}

async function extractPageContent(): Promise<string> {
  // Check if this is a YouTube page
  if (isYouTubeUrl(window.location.href)) {
    return await extractYouTubeContent();
  }

  // Detect if this is a Substack article
  const isSubstack = isSubstackUrl();

  // For Substack, use a specialized extraction approach
  if (isSubstack) {
    return await extractSubstackContent();
  }

  // Use Readability for general pages with hybrid References extraction
  try {
    // Create a proper Document object for Readability
    // Using document.cloneNode(true) creates a proper document clone
    const documentClone = document.cloneNode(true) as Document;
    
    // HYBRID APPROACH: Extract References section BEFORE Readability processes the document
    // This ensures we preserve it even if Readability's heuristics exclude it
    const savedReferencesHtml = findReferencesSection(documentClone);
    
    // Apply selective cleanup to remove unwanted elements
    // This removes navigation, ads, and promotional content while preserving
    // the document structure that Readability needs
    selectiveCleanup(documentClone, false);
    
    const article = new Readability(documentClone).parse();
    
    if (article && article.content) {
      // Initialize Turndown with appropriate options
      const turndownService = new TurndownService({
        headingStyle: 'atx',
        codeBlockStyle: 'fenced',
      });

      // Strip scripts and styles during conversion
      turndownService.remove(['script', 'style']);

      // Convert HTML to Markdown
      let markdown = turndownService.turndown(article.content);

      // Apply post-processing cleanup
      markdown = cleanMarkdownContent(markdown, false);
      
      // HYBRID APPROACH: If References were saved but not in final markdown, append them
      let referencesMarkdown = '';
      if (savedReferencesHtml && !markdown.toLowerCase().includes('reference')) {
        // Convert saved References HTML to markdown
        const turndownService = new TurndownService({
          headingStyle: 'atx',
          codeBlockStyle: 'fenced',
        });
        turndownService.remove(['script', 'style']);
        
        referencesMarkdown = turndownService.turndown(savedReferencesHtml);
      }

      // Add title and byline header
      let content = `# ${article.title}\n\n`;
      if (article.byline) {
        content += `**By:** ${article.byline}\n\n`;
      }
      content += markdown;
      
      // Append References if they were saved and excluded
      if (referencesMarkdown) {
        content += '\n\n' + referencesMarkdown;
      }

      return content;
    }
  } catch (error) {
    console.error('Readability extraction failed:', error);
  }

  // Fallback to simple extraction
  return extractSimpleContent();
}

async function extractSubstackContent(): Promise<string> {
  try {
    // Substack-specific selectors (in priority order)
    const contentSelectors = [
      '.body.markup',        // Main article body in Substack
      'article .body',       // Article body
      '.post-content',       // Post content wrapper
      '.available-content',  // Available content section
      'article',             // Generic article tag
      'main',                // Main content area
    ];

    let contentElement: Element | null = null;
    
    // Try each selector until we find content
    for (const selector of contentSelectors) {
      const element = document.querySelector(selector);
      if (element && element.innerHTML && element.innerHTML.length > 200) {
        contentElement = element;
        console.log(`Found Substack content using selector: ${selector}`);
        break;
      }
    }

    if (!contentElement) {
      console.warn('No Substack content found with specific selectors, falling back to Readability');
      return extractWithReadability(true);
    }

    // Get title from h1 or meta tags
    const titleElement = document.querySelector('h1.post-title, h1');
    const title = titleElement?.textContent?.trim() || document.title;

    // Get author from meta or byline
    const authorElement = document.querySelector('.author-name, [rel="author"]');
    const author = authorElement?.textContent?.trim() || '';

    // Initialize Turndown for Substack extraction
    const turndownService = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced',
    });

    // Strip scripts and styles during conversion
    turndownService.remove(['script', 'style']);

    // Convert HTML to Markdown
    let markdown = turndownService.turndown(contentElement.innerHTML);

    // Apply conservative post-processing cleanup for Substack
    markdown = cleanMarkdownContent(markdown, true);

    // Build final content with title and author
    let content = `# ${title}\n\n`;
    if (author) {
      content += `**By:** ${author}\n\n`;
    }
    content += markdown;

    return content;
  } catch (error) {
    console.error('Substack extraction failed:', error);
    // Fallback to Readability with Substack-aware cleanup
    return extractWithReadability(true);
  }
}

async function extractWithReadability(isSubstack: boolean = false): Promise<string> {
  try {
    // Create a proper Document object for Readability
    const documentClone = document.cloneNode(true) as Document;
    
    // Extract References section BEFORE Readability processes the document
    const savedReferencesHtml = findReferencesSection(documentClone);
    
    // Apply selective cleanup with Substack awareness
    selectiveCleanup(documentClone, isSubstack);
    
    const article = new Readability(documentClone).parse();
    
    if (article && article.content) {
      // Initialize Turndown with appropriate options
      const turndownService = new TurndownService({
        headingStyle: 'atx',
        codeBlockStyle: 'fenced',
      });

      // Strip scripts and styles during conversion
      turndownService.remove(['script', 'style']);

      // Convert HTML to Markdown
      let markdown = turndownService.turndown(article.content);

      // Apply post-processing cleanup
      markdown = cleanMarkdownContent(markdown, isSubstack);
      
      // HYBRID APPROACH: If References were saved but not in final markdown, append them
      let referencesMarkdown = '';
      if (savedReferencesHtml && !markdown.toLowerCase().includes('reference')) {
        // Convert saved References HTML to markdown
        const refTurndown = new TurndownService({
          headingStyle: 'atx',
          codeBlockStyle: 'fenced',
        });
        refTurndown.remove(['script', 'style']);
        
        referencesMarkdown = refTurndown.turndown(savedReferencesHtml);
      }

      // Add title and byline header
      let content = `# ${article.title}\n\n`;
      if (article.byline) {
        content += `**By:** ${article.byline}\n\n`;
      }
      content += markdown;
      
      // Append References if they were saved and excluded
      if (referencesMarkdown) {
        content += '\n\n' + referencesMarkdown;
      }

      return content;
    }
  } catch (error) {
    console.error('Readability extraction failed:', error);
  }

  // Fallback to simple extraction
  return extractSimpleContent();
}
/**
 * Format timestamp from seconds to MM:SS
 */
function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format YouTube metadata only (when transcript is not available)
 * Returns just a placeholder message (NO metadata header)
 */
function formatMetadataOnly(_metadata: any): string {
  return '[Transcript not available or extraction failed]';
}

/**
 * Format transcript as plain text paragraphs (NO metadata header)
 * Metadata should be sent separately when uploading to backend
 * Groups segments into readable paragraphs without timestamps
 */
function formatTranscriptMarkdown(_metadata: any, segments: Array<{ time: string; text: string; seconds: number; durationSeconds: number }>): string {
  let markdown = '';

  // Group segments into paragraphs for better readability (NO metadata header - matches server-side behavior)
  let currentParagraph: string[] = [];
  let lastEndSeconds = 0;
  
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    
    // Skip empty segments entirely - don't process them at all
    if (!segment.text) {
      continue;
    }
    
    const timeSinceLastSegment = segment.seconds - lastEndSeconds;
    
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
      markdown += `${paragraphText}\n\n`;
      currentParagraph = [];
    }
    
    // Add text to paragraph and update last end time
    currentParagraph.push(segment.text);
    lastEndSeconds = segment.seconds + segment.durationSeconds;
  }
  
  // Write out the final paragraph
  if (currentParagraph.length > 0) {
    const paragraphText = currentParagraph.join(' ');
    markdown += `${paragraphText}\n\n`;
  }

  return markdown;
}

async function extractYouTubeContent(): Promise<string> {
  try {
    console.log('='.repeat(80));
    console.log('[Content Script] EXTRACTION PATH: content-script.ts');
    console.log('[Content Script] Requesting YouTube extraction from background script');
    console.log('='.repeat(80));
    
    // Get metadata and transcript XML from background script
    const response = await chrome.runtime.sendMessage({
      type: 'EXTRACT_YOUTUBE_FROM_TAB'
    });

    if (!response.success || !response.metadata) {
      throw new Error('Failed to extract metadata');
    }

    const metadata = response.metadata;

    // Store channel name for potential use by the extension
    // The channel name will be used by the background script when uploading
    (window as any).__youtubeChannelName = metadata.channelName || metadata.author;

    // Check if we got transcript XML from MAIN world
    if (response.transcriptXml && response.transcriptXml.length > 0) {
      // Parse the XML - YouTube uses <p> tags with t (time) and d (duration) attributes
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(response.transcriptXml, 'text/xml');
      const textElements = xmlDoc.querySelectorAll('p');
      
      if (textElements.length > 0) {
        const transcriptLines: Array<{ time: string; text: string; seconds: number; durationSeconds: number }> = [];
        
        for (const element of Array.from(textElements)) {
          const start = element.getAttribute('t'); // time in milliseconds
          const duration = element.getAttribute('d'); // duration in milliseconds
          const text = element.textContent;
          
          if (start && text) {
            const seconds = parseFloat(start) / 1000; // Convert ms to seconds
            const durationSeconds = duration ? parseFloat(duration) / 1000 : 0; // Convert ms to seconds
            const time = formatTimestamp(seconds);
            // Replace internal newlines and multiple spaces with single space, then trim
            // This matches server-side .strip() behavior
            const cleanText = text.replace(/\s+/g, ' ').trim();
            
            // Store the CLEANED text in the segment
            transcriptLines.push({ time, text: cleanText, seconds, durationSeconds });
          }
        }
        
        if (transcriptLines.length > 0) {
          const content = formatTranscriptMarkdown(metadata, transcriptLines);
          return content;
        }
      }
    }

    // Fallback to metadata only
    const content = formatMetadataOnly(metadata);
    return content;

  } catch (error) {
    console.error('YouTube extraction error:', error);
    return extractYouTubeMetadataOnly();
  }
}

function extractYouTubeMetadataOnly(): string {
  try {
    // Get video title
    const titleElement = document.querySelector('h1.ytd-video-primary-info-renderer, h1.title');
    const title = titleElement?.textContent?.trim() || 'YouTube Video';

    // Get channel name
    const channelElement = document.querySelector('#channel-name a, ytd-channel-name a');
    const channel = channelElement?.textContent?.trim() || '';

    // Get description
    const descriptionElement = document.querySelector('#description, #description-text');
    const description = descriptionElement?.textContent?.trim() || '';

    // Build content with metadata only
    let content = `# ${title}\n\n`;
    if (channel) {
      content += `**Channel:** ${channel}\n\n`;
    }
    if (description) {
      content += `## Description\n\n${description}\n\n`;
    }
    
    // Add note that transcript extraction failed
    content += `## Transcript\n\n[Transcript extraction failed - will be attempted by backend]`;

    return content;
  } catch (error) {
    console.error('YouTube metadata extraction failed:', error);
    return extractSimpleContent();
  }
}

function extractSimpleContent(): string {
  // Try to find main content area using semantic HTML5 and CMS patterns
  const selectors = [
    // Semantic HTML5
    'article[role="article"]',
    'article',
    'main[role="main"]',
    'main',
    '[role="main"]',
    
    // Common CMS patterns (WordPress, Medium, Ghost, etc.)
    '.post-content',
    '.entry-content',
    '.article-content',
    '.content-body',
    '.article-body',
    '.post-body',
    
    // News sites (IndieWire, etc.)
    '.article__body',
    '.story-body',
    '.news-article',
    
    // Generic fallbacks
    '.main-content',
    '#main-content',
    '.content',
    '#content',
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element && element.innerHTML && element.innerHTML.length > 200) {
      try {
        // Initialize Turndown for fallback extraction
        const turndownService = new TurndownService({
          headingStyle: 'atx',
          codeBlockStyle: 'fenced',
        });

        // Strip scripts and styles during conversion
        turndownService.remove(['script', 'style']);

        // Convert HTML to Markdown
        let markdown = turndownService.turndown(element.innerHTML);

        // Apply post-processing cleanup
        markdown = cleanMarkdownContent(markdown);

        return markdown;
      } catch (error) {
        console.error('Turndown conversion failed in fallback:', error);
        // Fall back to textContent if Turndown fails
        return element.textContent?.trim() || '';
      }
    }
  }

  // If no selector worked, try to find the largest content container (heuristic)
  try {
    const elements = Array.from(document.querySelectorAll('div, section'));
    
    // Filter out elements that are likely navigation/ads/footer
    const filtered = elements.filter(el => {
      const classes = el.className?.toLowerCase() || '';
      const id = el.id?.toLowerCase() || '';
      const combined = classes + ' ' + id;
      
      // Skip obvious non-content elements
      if (combined.includes('nav') ||
          combined.includes('header') ||
          combined.includes('footer') ||
          combined.includes('sidebar') ||
          combined.includes('menu') ||
          combined.includes('ad-') ||
          combined.includes('cookie') ||
          combined.includes('consent')) {
        return false;
      }
      return true;
    });
    
    // Find element with most paragraph content (better indicator of article text)
    let maxScore = 0;
    let bestElement: Element | null = null;
    
    for (const el of filtered) {
      const textLength = el.textContent?.length || 0;
      const paragraphs = el.querySelectorAll('p').length;
      
      // Score based on text length and paragraph count
      // Paragraphs are a strong indicator of article content
      const score = textLength + (paragraphs * 200);
      
      if (score > maxScore && textLength > 500) {
        maxScore = score;
        bestElement = el;
      }
    }
    
    if (bestElement) {
      console.log('Found content using largest container heuristic');
      const turndownService = new TurndownService({
        headingStyle: 'atx',
        codeBlockStyle: 'fenced',
      });
      turndownService.remove(['script', 'style']);
      
      let markdown = turndownService.turndown(bestElement.innerHTML);
      markdown = cleanMarkdownContent(markdown);
      
      return markdown;
    }
  } catch (error) {
    console.error('Largest container heuristic failed:', error);
  }

  // Last resort: get body text
  return document.body.textContent?.trim() || '';
}

/**
 * Extract metadata from the current page (Open Graph, meta tags, etc.)
 */
function extractPageMetadata(): {
  title?: string;
  description?: string;
  image?: string;
} {
  const metadata: {
    title?: string;
    description?: string;
    image?: string;
  } = {};

  // Try Open Graph title first
  const ogTitle = document.querySelector('meta[property="og:title"]')?.getAttribute('content');
  if (ogTitle) {
    metadata.title = ogTitle;
  } else {
    // Fallback to page title
    const titleElement = document.querySelector('title');
    if (titleElement?.textContent) {
      metadata.title = titleElement.textContent.trim();
    }
  }

  // Try Open Graph description
  const ogDescription = document.querySelector('meta[property="og:description"]')?.getAttribute('content');
  if (ogDescription) {
    metadata.description = ogDescription;
  } else {
    // Fallback to meta description
    const metaDescription = document.querySelector('meta[name="description"]')?.getAttribute('content');
    if (metaDescription) {
      metadata.description = metaDescription;
    }
  }

  // Try Open Graph image
  const ogImage = document.querySelector('meta[property="og:image"]')?.getAttribute('content');
  if (ogImage) {
    metadata.image = ogImage;
  } else {
    // Fallback to Twitter image
    const twitterImage = document.querySelector('meta[name="twitter:image"]')?.getAttribute('content');
    if (twitterImage) {
      metadata.image = twitterImage;
    }
  }

  return metadata;
}

// Export for use in injected scripts
(window as any).ContentStashExtractor = {
  extractPageContent,
  extractYouTubeContent,
  extractSimpleContent,
  extractPageMetadata,
};
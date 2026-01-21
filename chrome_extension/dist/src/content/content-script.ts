// Content script for extracting page content
// This runs in the context of web pages

import { Readability } from '@mozilla/readability';
import TurndownService from 'turndown';

// Listen for extraction requests from background script
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'EXTRACT_CONTENT') {
    try {
      const content = extractPageContent();
      sendResponse({ success: true, content });
    } catch (error) {
      sendResponse({ success: false, error: (error as Error).message });
    }
    return true;
  }
});

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
function cleanMarkdownContent(content: string): string {
  const lines = content.split('\n');
  const cleanedLines: string[] = [];
  let inJsonBlock = false;
  let inFeaturedSection = false;
  let inPromotionalBlock = false;
  let pastMainContent = false;

  for (const line of lines) {
    const stripped = line.trim();
    const lowerLine = stripped.toLowerCase();
    
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
    if (pastMainContent && !inPromotionalBlock && stripped.startsWith('![')) {
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

    cleanedLines.push(line);
  }

  // Join lines and remove excessive blank lines (more than 2 consecutive)
  let cleaned = cleanedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
}

/**
 * Selectively remove unwanted elements from the DOM without breaking document structure
 * This function removes navigation, ads, and promotional content while preserving
 * the main document structure (documentElement, body) that Readability needs
 */
function selectiveCleanup(doc: Document): void {
  // Remove unwanted structural elements
  const structuralSelectors = [
    'nav',
    'header',
    'footer',
    'aside',
    '[role="navigation"]',
    '[role="banner"]',
    '[role="complementary"]',
  ];

  structuralSelectors.forEach(selector => {
    const elements = doc.querySelectorAll(selector);
    elements.forEach(el => el.remove());
  });

  // Remove elements with unwanted class/id patterns
  const unwantedPatterns = [
    /featured/i,
    /related/i,
    /recommended/i,
    /social/i,
    /share/i,
    /comment/i,
    /sidebar/i,
    /advertisement/i,
    /\bad\b/i,
    /promo/i,
    /newsletter/i,
    /subscribe/i,
    /follow/i,
  ];
  
  // Check all elements for unwanted patterns in class or id
  const allElements = doc.querySelectorAll('*');
  allElements.forEach(el => {
    const className = el.className?.toString() || '';
    const id = el.id || '';
    const combined = `${className} ${id}`;

    // Don't remove body or documentElement
    if (el === doc.body || el === doc.documentElement) {
      return;
    }

    // Check if element matches any unwanted pattern
    for (const pattern of unwantedPatterns) {
      if (pattern.test(combined)) {
        el.remove();
        break;
      }
    }
  });
}

function extractPageContent(): string {
  // Check if this is a YouTube page
  if (window.location.hostname.includes('youtube.com')) {
    return extractYouTubeContent();
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
    selectiveCleanup(documentClone);
    
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
      markdown = cleanMarkdownContent(markdown);
      
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

function extractYouTubeContent(): string {
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

    // Try to get transcript if available
    let transcript = '';
    const transcriptButton = document.querySelector('[aria-label*="transcript" i], [aria-label*="Show transcript" i]');
    if (transcriptButton) {
      // Note: Actually clicking and extracting transcript requires more complex logic
      // For now, we'll just note that a transcript might be available
      transcript = '\n\n[Transcript available but not extracted in this version]';
    }

    let content = `# ${title}\n\n`;
    if (channel) {
      content += `**Channel:** ${channel}\n\n`;
    }
    if (description) {
      content += `## Description\n\n${description}`;
    }
    content += transcript;

    return content;
  } catch (error) {
    console.error('YouTube extraction failed:', error);
    return extractSimpleContent();
  }
}

function extractSimpleContent(): string {
  // Try to find main content area
  const selectors = [
    'main',
    'article',
    '[role="main"]',
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

  // Last resort: get body text
  return document.body.textContent?.trim() || '';
}

// Export for use in injected scripts
(window as any).ContentStashExtractor = {
  extractPageContent,
  extractYouTubeContent,
  extractSimpleContent,
};